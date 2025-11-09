from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


from .models import Product, Order, OrderItem
import json


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse(
        [
            {
                "title": "Burger",
                "src": static("burger.jpg"),
                "text": "Tasty Burger at your door step",
            },
            {
                "title": "Spices",
                "src": static("food.jpg"),
                "text": "All Cuisines",
            },
            {
                "title": "New York",
                "src": static("tasty.jpg"),
                "text": "Food is incomplete without a tasty dessert",
            },
        ],
        safe=False,
        json_dumps_params={
            "ensure_ascii": False,
            "indent": 4,
        },
    )


def product_list_api(request):
    products = Product.objects.select_related("category").available()

    dumped_products = []
    for product in products:
        dumped_product = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "special_status": product.special_status,
            "description": product.description,
            "category": (
                {
                    "id": product.category.id,
                    "name": product.category.name,
                }
                if product.category
                else None
            ),
            "image": product.image.url,
            "restaurant": {
                "id": product.id,
                "name": product.name,
            },
        }
        dumped_products.append(dumped_product)
    return JsonResponse(
        dumped_products,
        safe=False,
        json_dumps_params={
            "ensure_ascii": False,
            "indent": 4,
        },
    )


@api_view(["POST"])
def register_order(request):
    try:
        order_data = request.data
        required_fields = [
            "firstname",
            "lastname",
            "phonenumber",
            "address",
            "products",
        ]
        missing_fields = [
            field for field in required_fields if not order_data.get(field)
        ]

        if missing_fields:
            return Response(
                {
                    "error": f'Не заполнены обязательные поля: {", ".join(missing_fields)}'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(order_data["products"], list):
            return Response(
                {"error": "Поле 'products' должно быть списком"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        products_to_add = []
        for product_data in order_data["products"]:
            product_id = product_data.get("product")
            quantity = product_data.get("quantity", 1)

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"error": f"Товар с ID {product_id} не найден"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if quantity < 1 or quantity > 100:
                return Response(
                    {
                        "error": f"Количество товара {product.name} должно быть от 1 до 100"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            products_to_add.append((product, quantity))

        with transaction.atomic():
            order = Order.objects.create(
                firstname=order_data["firstname"].strip(),
                lastname=order_data["lastname"].strip(),
                phonenumber=order_data["phonenumber"].strip(),
                address=order_data["address"].strip(),
            )

            order_items = [
                OrderItem(order=order, product=product, quantity=quantity)
                for product, quantity in products_to_add
            ]

            OrderItem.objects.bulk_create(order_items)

        order_items = order.items.select_related("product").all()
        total_cost = sum(item.get_total_price() for item in order_items)

        response_data = {
            "id": order.id,
            "firstname": order.firstname,
            "lastname": order.lastname,
            "phonenumber": str(order.phonenumber),
            "address": order.address,
            "created_at": order.created_at.isoformat(),
            "total_cost": str(total_cost),
            "products": [
                {
                    "id": item.product.id,
                    "name": item.product.name,
                    "quantity": item.quantity,
                    "price": str(item.product.price),
                    "total_price": str(item.get_total_price()),
                }
                for item in order_items
            ],
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as err:
        return Response(
            {"error": f"Внутренняя ошибка сервера: {str(err)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
