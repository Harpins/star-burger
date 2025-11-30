from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    OrderCreateSerializer,
    OrderItemCreateSerializer,
    OrderItemResponseSerializer,
)
from .models import Product, Order


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
@transaction.atomic()
def register_order(request):
    serializer = OrderCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    order = serializer.save()

    order_with_data = (
        Order.objects
        .with_total_price()
        .prefetch_related('items__product')
        .get(id=order.id)
    )

    response_data = {
        "id": order_with_data.id,
        "firstname": order_with_data.firstname,
        "lastname": order_with_data.lastname,
        "phonenumber": str(order_with_data.phonenumber),
        "address": order_with_data.address,
        "created_at": order_with_data.created_at.isoformat(),
        "products": OrderItemResponseSerializer(
            order_with_data.items.all(), many=True
        ).data,
        "total_cost": order_with_data.total_price or 0,
    }

    return Response(response_data, status=status.HTTP_201_CREATED)
