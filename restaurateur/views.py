from django import forms
from django.shortcuts import redirect, render
from django.db.models import Prefetch
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant, Order, OrderItem

from foodcartapp.utils import fetch_coordinates, calculate_distance

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
    orders = Order.objects.filter(status__in=["un", "pr", "sh"]).prefetch_related(
        Prefetch(
            "items",
            queryset=OrderItem.objects.select_related("product")
        )
    ).order_by("-created_at")

    for order in orders:
        order.total_price = sum(item.get_total_price() for item in order.items.all())

        customer_lon, customer_lat = None, None
        if order.address:
            customer_coords = order.get_customer_coordinates()
            if customer_coords:
                customer_lon, customer_lat = customer_coords

        if order.items.exists():
            restaurant_sets = [
                set(item.product.available_restaurants()) for item in order.items.all()
            ]
            possible_restaurants = list(set.intersection(*restaurant_sets)) if restaurant_sets else []
        else:
            possible_restaurants = []

        restaurants_with_distance = []
        for restaurant in possible_restaurants:
            if customer_lat is not None and customer_lon is not None and restaurant.latitude and restaurant.longitude:
                distance = calculate_distance(
                    customer_lat, customer_lon,
                    float(restaurant.latitude), float(restaurant.longitude)
                )
                distance_rounded = round(distance, 2)
            else:
                distance_rounded = None

            restaurants_with_distance.append({
                "restaurant": restaurant,
                "distance": distance_rounded,
            })

        restaurants_with_distance.sort(key=lambda x: (x["distance"] is None, x["distance"]))

        order.can_cook_here = restaurants_with_distance

        if order.cooking_restaurant:
            if customer_lat is not None and customer_lon is not None and order.cooking_restaurant.latitude and order.cooking_restaurant.longitude:
                current_distance = calculate_distance(
                    customer_lat, customer_lon,
                    float(order.cooking_restaurant.latitude), float(order.cooking_restaurant.longitude)
                )
                order.distance_to_current_restaurant = round(current_distance, 2)
            else:
                order.distance_to_current_restaurant = None
        else:
            order.distance_to_current_restaurant = None

    context = {
        "orders": orders,
    }

    return render(request, "order_items.html", context)
