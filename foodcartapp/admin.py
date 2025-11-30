from django.contrib import admin
from django.shortcuts import reverse
from django.templatetags.static import static
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Sum, F

from .models import (
    Product,
    ProductCategory,
    Restaurant,
    RestaurantMenuItem,
    Order,
    OrderItem,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    min_num = 1
    readonly_fields = ["fixed_price"]

    fields = ["product", "quantity", "fixed_price"]


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0
    min_num = 1
    fields = ["restaurant", "product", "availability"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "status",
        "cooking_restaurant",
        "payment_type",
        "firstname",
        "lastname",
        "phonenumber",
        "address",
        "created_at",
        "called_at",
        "delivered_at",
        "get_total_order_price",
        "get_items_count",
        "commentary",
    ]

    list_filter = ["created_at", "status", "payment_type", "cooking_restaurant"]
    search_fields = [
        "firstname",
        "lastname",
        "phonenumber",
        "address",
        "status",
        "payment_type",
        "cooking_restaurant",
    ]
    readonly_fields = ["created_at", "get_total_order_price"]

    inlines = [OrderItemInline]

    fieldsets = [
        (
            "Информация о клиенте",
            {"fields": ["firstname", "lastname", "phonenumber", "address"]},
        ),
        ("Статус", {"fields": ["status"]}),
        ("Ресторан", {"fields": ["cooking_restaurant"]}),
        ("Оплата", {"fields": ["payment_type"]}),
        (
            "Даты",
            {
                "fields": ["created_at", "called_at", "delivered_at"],
                "classes": ["collapse"],
            },
        ),
        ("Итоговая стоимость", {"fields": ["get_total_order_price"]}),
        ("Комментарий", {"fields": ["commentary"]}),
    ]

    def get_total_order_price(self, obj):
        total = obj.items.aggregate(total=Sum(F("quantity") * F("fixed_price")))[
            "total"
        ]
        return f"{total} руб." if total else "0 руб."

    get_total_order_price.short_description = "Итоговая стоимость"

    def get_items_count(self, obj):
        return obj.items.count()

    get_items_count.short_description = "Кол-во позиций"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("items", "items__product")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "cooking_restaurant":
            order_id = request.resolver_match.kwargs.get("object_id")
            if not order_id:
                kwargs["queryset"] = Restaurant.objects.all()
                return super().formfield_for_foreignkey(db_field, request, **kwargs)
            try:
                order = Order.objects.prefetch_related("items__product").get(
                    id=order_id
                )
                available_restaurants = None
                for item in order.items.all():
                    restaurants = set(item.product.available_restaurants())
                    if available_restaurants is None:
                        available_restaurants = restaurants
                    else:
                        available_restaurants &= restaurants
                    if not available_restaurants:
                        break

                if available_restaurants:
                    queryset = Restaurant.objects.filter(
                        id__in=[r.id for r in available_restaurants]
                    )
                    kwargs["queryset"] = queryset.order_by("name")
                    kwargs["help_text"] = f"Доступно: {queryset.count()} рестор."
                else:
                    kwargs["queryset"] = Restaurant.objects.none()
                    kwargs["help_text"] = (
                        "<span style='color:red; font-weight:bold;'>"
                        "Нет ресторанов, которые могут приготовить этот заказ!"
                        "</span>"
                    )
            except Order.DoesNotExist:
                kwargs["queryset"] = Restaurant.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def response_post_save_change(self, request, obj):
        response = super().response_post_save_change(request, obj)
        if "next" in request.GET:
            next_url = request.GET["next"]
            allowed_host = request.get_host()
            if url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={allowed_host}, require_https=False
            ):
                return HttpResponseRedirect(next_url)
        return response


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = [
        "name",
        "location",
        "contact_phone",
    ]

    list_display = ["name", "contact_phone", "location"]
    inlines = [RestaurantMenuItemInline]

   

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["get_image_list_preview", "name", "category", "price", "id"]
    list_display_links = [
        "name",
    ]
    list_filter = [
        "category",
    ]
    search_fields = [
        # FIXME SQLite can not convert letter case for cyrillic words properly, so search will be buggy.
        # Migration to PostgreSQL is necessary
        "name",
        "category__name",
    ]

    inlines = [RestaurantMenuItemInline]
    fieldsets = (
        (
            "Общее",
            {
                "fields": [
                    "name",
                    "category",
                    "image",
                    "get_image_preview",
                    "price",
                ]
            },
        ),
        (
            "Подробно",
            {
                "fields": [
                    "special_status",
                    "description",
                ],
                "classes": ["wide"],
            },
        ),
    )

    readonly_fields = ["get_image_preview", "id"]

    class Media:
        css = {"all": (static("admin/foodcartapp.css"))}

    def get_image_preview(self, obj):
        if not obj.image:
            return "выберите картинку"
        return format_html(
            '<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url
        )

    get_image_preview.short_description = "превью"

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return "нет картинки"
        edit_url = reverse("admin:foodcartapp_product_change", args=(obj.id,))
        return format_html(
            '<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>',
            edit_url=edit_url,
            src=obj.image.url,
        )

    get_image_list_preview.short_description = "превью"


@admin.register(ProductCategory)
class ProductAdmin(admin.ModelAdmin):
    pass
