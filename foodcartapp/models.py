from django.db import models
from django.db.models import Sum, F, Prefetch
from django.db.models.query import QuerySet
from django.core.validators import MinValueValidator, MaxValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from collections import defaultdict


class OrderQuerySet(QuerySet):
    def with_total_price(self):
        return self.annotate(
            total_price=Sum(F("items__quantity") * F("items__fixed_price"))
        )

    def active(self):
        return self.filter(status__in=["un", "pr", "sh"])

    def for_manager_panel(self):
        return (
            self.active()
            .with_total_price()
            .select_related(
                "cooking_restaurant",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("product"),
                    to_attr="prefetched_items",
                ),
            )
        )


class OrderManager(models.Manager):
    def get_queryset(self):
        return OrderQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def with_total_price(self):
        return self.get_queryset().with_total_price()

    def for_manager_panel(self):
        orders = list(self.get_queryset().for_manager_panel().order_by("-created_at"))

        if not orders:
            return orders

        menu_items = list(
            RestaurantMenuItem.objects.filter(availability=True)
            .select_related("restaurant")
            .values("restaurant_id", "product_id")
        )

        restaurant_products = defaultdict(set)
        for item in menu_items:
            restaurant_products[item["restaurant_id"]].add(item["product_id"])

        restaurant_ids = restaurant_products.keys()
        restaurants_by_id = {
            restaurant.id: restaurant for restaurant in Restaurant.objects.filter(id__in=restaurant_ids)
        }

        for order in orders:
            order_items = getattr(order, "prefetched_items", [])
            if not order_items:
                order.available_restaurants = []
                continue

            order_product_ids = {item.product_id for item in order_items}

            available = []
            for rest_id, available_product_ids in restaurant_products.items():
                if order_product_ids.issubset(available_product_ids):
                    available.append(restaurants_by_id[rest_id])

            order.available_restaurants = available

        return orders


class Restaurant(models.Model):
    name = models.CharField("название", max_length=50)
    address = models.TextField(verbose_name="Адрес")
    contact_phone = models.CharField(
        "контактный телефон", max_length=50, blank=True, db_index=True
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
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    commentary = models.TextField(verbose_name="Комментарий", blank=True)

    payment_type = models.CharField(
        max_length=4,
        choices=PAYMENT_TYPES,
        default="nstd",
        verbose_name="Тип оплаты",
        db_index=True,
    )

    objects = OrderManager()

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заказ {self.id} от {self.firstname} {self.lastname} {self.phonenumber}"



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

    fixed_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Цена на момент заказа",
        editable=False,
        blank=True,
    )

    class Meta:
        verbose_name = "позиция в заказе"
        verbose_name_plural = "позиции в заказе"
        unique_together = [["order", "product"]]

    def __str__(self):
        return f"{self.product.name} x {self.quantity} (заказ #{self.order.id})"
