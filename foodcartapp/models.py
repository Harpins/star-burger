from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from .utils import fetch_coordinates, calculate_distance


class Restaurant(models.Model):
    name = models.CharField("название", max_length=50)
    address = models.CharField(
        "адрес",
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        "контактный телефон", max_length=50, blank=True, db_index=True
    )

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Широта"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Долгота"
    )

    class Meta:
        verbose_name = "ресторан"
        verbose_name_plural = "рестораны"

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = RestaurantMenuItem.objects.filter(availability=True).values_list(
            "product"
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField("название", max_length=50)

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField("название", max_length=50)
    category = models.ForeignKey(
        ProductCategory,
        verbose_name="категория",
        related_name="products",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        "цена", max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    image = models.ImageField("картинка")
    special_status = models.BooleanField(
        "спец.предложение",
        default=False,
        db_index=True,
    )
    description = models.TextField(
        "описание",
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"

    def available_restaurants(self):
        return Restaurant.objects.filter(
            menu_items__product=self, menu_items__availability=True
        ).distinct()

    def __str__(self):
        return f"{self.name} - {self.price}"


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name="menu_items",
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="menu_items",
        verbose_name="продукт",
    )
    availability = models.BooleanField("в продаже", default=False, db_index=True)

    class Meta:
        verbose_name = "пункт меню ресторана"
        verbose_name_plural = "пункты меню ресторана"
        unique_together = [["restaurant", "product"]]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class Order(models.Model):
    ORDER_STATUSES = {
        "un": "Необработан",
        "pr": "Готовится",
        "sh": "Отправлен",
        "dl": "Доставлен",
    }
    PAYMENT_TYPES = {
        "nstd": "Не установлен",
        "epay": "Электронно",
        "cash": "Наличными",
    }
    firstname = models.CharField(
        max_length=100, verbose_name="Имя", null=False, blank=False
    )
    lastname = models.CharField(
        max_length=100, verbose_name="Фамилия", null=False, blank=False
    )
    phonenumber = PhoneNumberField(
        verbose_name="Телефон", help_text="В формате +7 XXX XXX-XX-XX"
    )
    address = models.TextField(verbose_name="Адрес", null=False, blank=False)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Создан", db_index=True
    )
    called_at = models.DateTimeField(
        editable=True, verbose_name="Время звонка", null=True, blank=True, db_index=True
    )
    delivered_at = models.DateTimeField(
        editable=True, verbose_name="Доставлен", blank=True, null=True, db_index=True
    )

    status = models.CharField(
        max_length=2,
        choices=ORDER_STATUSES,
        default="un",
        verbose_name="Статус",
        db_index=True,
    )

    cooking_restaurant = models.ForeignKey(
        Restaurant,
        verbose_name="Ресторан-исполнитель",
        related_name="orders",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    distance_to_restaurant = models.DecimalField(
        "расстояние до ресторана (км)",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    commentary = models.TextField(verbose_name="Комментарий", blank=True, null=True)

    payment_type = models.CharField(
        max_length=4,
        choices=PAYMENT_TYPES,
        default="nstd",
        verbose_name="Тип оплаты",
        db_index=True,
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заказ {self.id} от {self.firstname} {self.lastname} {self.phonenumber}"

    def get_customer_coordinates(self):
        if not self.address:
            return None
        return fetch_coordinates(self.address)

    def calculate_distance_to_restaurant(self, restaurant):
        if not restaurant.latitude or not restaurant.longitude:
            return None

        client_coords = self.get_customer_coordinates()
        if not client_coords:
            return None
        client_lon, client_lat = client_coords
        rest_lat = float(restaurant.latitude)
        rest_lon = float(restaurant.longitude)
        distance = calculate_distance(client_lat, client_lon, rest_lat, rest_lon)
        return distance


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, verbose_name="Заказ", related_name="items", on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        verbose_name="Продукт",
        related_name="order_items",
        on_delete=models.CASCADE,
    )

    quantity = models.PositiveIntegerField(
        verbose_name="Количество",
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        default=1,
    )

    price_at_order = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Цена на момент заказа",
        editable=False,
        default=0,
    )

    class Meta:
        verbose_name = "позиция в заказе"
        verbose_name_plural = "позиции в заказе"
        unique_together = [["order", "product"]]

    def __str__(self):
        return f"{self.product.name} x {self.quantity} (заказ #{self.order.id})"

    def get_total_price(self):
        return self.quantity * self.price_at_order
