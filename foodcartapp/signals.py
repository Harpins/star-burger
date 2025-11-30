from django.db.models.signals import pre_save
from django.dispatch import receiver
from geolocation.utils import fetch_coordinates
from .models import OrderItem, Order
from geolocation.models import Location


@receiver(pre_save, sender=OrderItem)
def set_fixed_price(sender, instance, **kwargs):
    if not instance.pk and instance.product:
        instance.fixed_price = instance.product.price


@receiver(pre_save, sender=Order)
def auto_fill_order_location(sender, instance, **kwargs):
    if instance.location_id:
        return

    raw_address = instance.address
    if not raw_address or not str(raw_address).strip():
        return

    address = str(raw_address).strip()

    location, created = Location.objects.get_or_create(
        address__iexact=address,
        defaults={'address': address}  
    )

    if not created:
        instance.location = location
        return


    coords = fetch_coordinates(address)
    if coords:
        lon, lat = coords
        location.latitude = lat
        location.longitude = lon
    else:
        location.latitude = None
        location.longitude = None

    location.save(update_fields=['latitude', 'longitude'])
    instance.location = location
