from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import OrderItem

@receiver(pre_save, sender=OrderItem)
def set_price_at_order(sender, instance, **kwargs):
    if not instance.pk and instance.product:
        instance.price_at_order = instance.product.price