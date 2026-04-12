from django import forms
from django.shortcuts import redirect, render
from django.db.models import Prefetch
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant, Order

from geolocation.models import Location
from geolocation.utils import fetch_coordinates, calculate_distance

import logging

logger = logging.getLogger(__name__)


class Login(forms.Form):
    username = forms.CharField(
        label="Логин",
        max_length=75,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Укажите имя пользователя"}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        max_length=75,
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Введите пароль"}
        ),
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={"form": form})

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(
            request,
            "login.html",
            context={
                "form": form,
                "ivalid": True,
            },
        )


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("restaurateur:login")


def is_manager(user):
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name="manager").exists()
    )


def normalize_address(address):
    if not address:
        return ""
    return address.strip().lower()


def get_or_create_locations(addresses):
    if not addresses:
        return {}

    unique_addresses = {
        normalize_address(addr)
        for addr in addresses
        if addr and normalize_address(addr)
    }
    if not unique_addresses:
        return {}

    existing_locations = Location.objects.filter(address__in=unique_addresses)
    location_by_address = {
        loc.address: (loc.latitude, loc.longitude) for loc in existing_locations
    }

    missing_addresses = unique_addresses - location_by_address.keys()

    if missing_addresses:
        for address in missing_addresses:
            coordinates = fetch_coordinates(address)
            if coordinates:
                lat, lon = coordinates
                location, created = Location.objects.get_or_create(
                    address=address, defaults={"latitude": lat, "longitude": lon}
                )
                location_by_address[address] = (location.latitude, location.longitude)
            else:
                location_by_address[address] = None

    for addr in unique_addresses:
        location_by_address.setdefault(addr, None)

    return location_by_address


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_products(request):
    restaurants = list(Restaurant.objects.order_by("name"))
    products = list(Product.objects.prefetch_related("menu_items"))

    products_with_restaurant_availability = []
    for product in products:
        availability = {
            item.restaurant_id: item.availability for item in product.menu_items.all()
        }
        ordered_availability = [
            availability.get(restaurant.id, False) for restaurant in restaurants
        ]

        products_with_restaurant_availability.append((product, ordered_availability))

    return render(
        request,
        template_name="products_list.html",
        context={
            "products_with_restaurant_availability": products_with_restaurant_availability,
            "restaurants": restaurants,
        },
    )


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_restaurants(request):
    return render(
        request,
        template_name="restaurants_list.html",
        context={
            "restaurants": Restaurant.objects.all(),
        },
    )


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_orders(request):
    orders = Order.objects.for_manager_panel()
    if not orders:
        return render(request, "order_items.html", {"orders": []})
    order_addresses = [order.address for order in orders if order.address.strip()]
    restaurant_addresses = list(
        Restaurant.objects.exclude(address__exact="")
        .values_list("address", flat=True)
        .distinct()
    )

    all_addresses = set(order_addresses + restaurant_addresses)
    coordinates_by_address = get_or_create_locations(all_addresses)

    for order in orders:
        normalized_addr = normalize_address(order.address)
        order_coords = coordinates_by_address.get(normalized_addr)
        if not order_coords:
            order.restaurant_distances = []
            continue
        distances = []
        for restaurant in order.available_restaurants:
            rest_normalized = normalize_address(restaurant.address)
            rest_coords = coordinates_by_address.get(rest_normalized)

            if rest_coords:
                distance = round(calculate_distance(order_coords, rest_coords), 2)
            else:
                distance = None

            distances.append(
                {
                    "restaurant": restaurant,
                    "distance": distance,
                }
            )

        distances.sort(key=lambda x: (x["distance"] is None, x["distance"]))
        order.restaurant_distances = distances

    return render(
        request,
        "order_items.html",
        {
            "orders": orders,
        },
    )

