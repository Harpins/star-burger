from django.db.models.signals import pre_save
from django.dispatch import receiver
from .utils import fetch_coordinates
from .models import OrderItem, Restaurant

@receiver(pre_save, sender=OrderItem)
def set_price_at_order(sender, instance, **kwargs):
    if not instance.pk and instance.product:
        instance.price_at_order = instance.product.price
        
@receiver(pre_save, sender=Restaurant)
def auto_fill_restaurant_coordinates(sender, instance, **kwargs):
    if instance.latitude is None or instance.longitude is None:
        if instance.address and instance.address.strip():
            coords = fetch_coordinates(instance.address.strip())
            if coords:
                instance.longitude, instance.latitude = coords