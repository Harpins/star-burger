from django.db.models.signals import pre_save
from django.dispatch import receiver
from geolocation.utils import fetch_coordinates
from .models import OrderItem, Order
from geolocation.models import Location


@receiver(pre_save, sender=OrderItem)
def set_fixed_price(sender, instance, **kwargs):
    if not instance.pk and instance.product:
        instance.fixed_price = instance.product.price


@receiver(pre_save, sender=Location)
def auto_fetch_coordinates(sender, instance, **kwargs):
    if instance.pk is not None:
        return

    if not instance.address:
        return

    address = instance.address.strip()
    if not address:
        return

    if instance.latitude is not None and instance.longitude is not None:
        return

    coords = fetch_coordinates(address)
    if coords:
        lon, lat = coords
        instance.longitude = lon
        instance.latitude = lat
        

@receiver(pre_save, sender=Order)
def auto_fill_order_location(sender, instance, **kwargs):
    if instance.location_id:  
        return
    
    raw_address = instance.address
    if not raw_address or not str(raw_address).strip():
        return
    
    address = str(raw_address).strip()

    existing_location = Location.objects.filter(address__iexact=address).first()
    if existing_location:
        instance.location = existing_location
        return

    coords = fetch_coordinates(address)
    if not coords:
        instance.location = Location.objects.create(
            address=address,
            latitude=None,
            longitude=None
        )
        return

    lon, lat = coords
    instance.location = Location.objects.create(
        address=address,
        latitude=lat,
        longitude=lon
    )
