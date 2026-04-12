from rest_framework import serializers
from .models import Order, OrderItem, Product
from geolocation.models import Location
from phonenumber_field.phonenumber import PhoneNumber
from django.db import transaction
from geolocation.utils import fetch_coordinates


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
    
    def validate(self, data):
        address = str(data["address"]).strip()
        if not address:
            raise serializers.ValidationError({"address": "Адрес не может быть пустым"})

        location = Location.objects.filter(address__iexact=address).first()
        if location and location.latitude is not None and location.longitude is not None:
            data["_location_cache"] = location
            return data

        coords = fetch_coordinates(address)
        if not coords:
            raise serializers.ValidationError({
                "address": "Не удалось определить координаты по адресу. Укажите точный адрес."
            })

        data["_location_cache"] = None  
        data["_coordinates"] = coords
        data["address"] = address 
        return data

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("_location_cache", None)
        validated_data.pop("_coordinates", None)
        items_data = validated_data.pop("products")
        address = validated_data["address"]

        order = Order.objects.create(**validated_data)

        location_cache = validated_data.get("_location_cache")
        if location_cache:
            pass
        else:
            coords = validated_data.get("_coordinates")
            if coords:
                lon, lat = coords
                Location.objects.update_or_create(
                    address__iexact=address,
                    defaults={
                        "address": address,
                        "latitude": lat,
                        "longitude": lon,
                    }
                )

        order_items = []
        for item in items_data:
            product = item["product_id"] 
            order_items.append(OrderItem(
                order=order,
                product=product,
                quantity=item["quantity"],
                fixed_price=product.price, 
            ))

        OrderItem.objects.bulk_create(order_items)

        return order
