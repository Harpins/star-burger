from django.db import models


class AddressCache(models.Model):
    address = models.CharField("Адрес", max_length=200, unique=True)
    longitude = models.DecimalField(
        "Долгота", max_digits=9, decimal_places=6, null=True, blank=True
    )
    latitude = models.DecimalField(
        "Широта", max_digits=9, decimal_places=6, null=True, blank=True
    )
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    fetched_at = models.DateTimeField("Найдено", auto_now_add=True)

    class Meta:
        verbose_name = "Кэш геокодирования"
        verbose_name_plural = "Кэш геокодирования"

    def __str__(self):
        return f"{self.address} → ({self.longitude}, {self.latitude})"
