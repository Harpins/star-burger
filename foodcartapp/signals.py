from django.db.models.signals import pre_save
from django.dispatch import receiver
from .utils import fetch_coordinates
from .models import OrderItem, Restaurant, Order, Location


@receiver(pre_save, sender=OrderItem)
def set_fixed_price(sender, instance, **kwargs):
    if not instance.pk and instance.product:
        instance.fixed_price = instance.product.price


@receiver(pre_save, sender=Restaurant)
def auto_fill_restaurant_location(sender, instance, **kwargs):
    if instance.location:
        return

    if not instance.location and instance.address.strip():
        address = instance.address.strip()

        existing_location = Location.objects.filter(address__iexact=address).first()
        if existing_location:
            instance.location = existing_location
            return

        coords = fetch_coordinates(address)
        if coords:
            lon, lat = coords
            location = Location.objects.create(
                address=address,
                latitude=lat,
                longitude=lon
            )
            instance.location = location


@receiver(pre_save, sender=Order)
def auto_fill_order_location(sender, instance, **kwargs):
    if instance.location:
        return

    if instance.address.strip():
        address = instance.address.strip()

        existing_location = Location.objects.filter(address__iexact=address).first()
        if existing_location:
            instance.location = existing_location
            return

        coords = fetch_coordinates(address)
        if coords:
            lon, lat = coords
            location = Location.objects.create(
                address=address,
                latitude=lat,
                longitude=lon
            )
            instance.location = location
