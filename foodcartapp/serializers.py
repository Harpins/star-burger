from rest_framework import serializers
from .models import Location, Order, OrderItem, Product
from phonenumber_field.phonenumber import PhoneNumber
from django.db import transaction
from .utils import fetch_coordinates


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price"]
        read_only_fields = ["id", "name", "price"]


class OrderItemCreateSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product_id", write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]


class OrderItemResponseSerializer(serializers.ModelSerializer):
    product = serializers.IntegerField(source="product_id", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]


class OrderCreateSerializer(serializers.ModelSerializer):
    products = OrderItemCreateSerializer(many=True, required=True, allow_empty=False)

    class Meta:
        model = Order
        fields = ["firstname", "lastname", "phonenumber", "address", "products"]

    def validate_phonenumber(self, value):
        try:
            phone = PhoneNumber.from_string(value)
            if not phone.is_valid():
                raise serializers.ValidationError("Неверный формат номера")
            return phone
        except Exception:
            raise serializers.ValidationError("Неверный формат номера")

    def validate_products(self, value):
        if not value:
            raise serializers.ValidationError("Заказ должен содержать хотя бы один товар")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            items_data = validated_data.pop("products")
            order = Order.objects.create(**validated_data)
            address = order.address.strip()
            if address:
                location, created = Location.objects.get_or_create(
                    address__iexact=address,
                    defaults={'address': address}
                )
                if created:
                    coords = fetch_coordinates(address)
                    if coords:
                        lon, lat = coords
                        location.longitude = lon
                        location.latitude = lat
                        location.save()
                order.location = location
                order.save(update_fields=['location'])  
            
            order_items = [
                OrderItem(
                    order=order,
                    product=item["product_id"],
                    quantity=item["quantity"],
                    fixed_price=item["product_id"].price,
                )
                for item in items_data
            ]
            OrderItem.objects.bulk_create(order_items)

            return order
