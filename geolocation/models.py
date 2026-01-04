from django.db import models

class Location(models.Model):
    address = models.CharField("полный адрес", max_length=200, unique=True)
    latitude = models.DecimalField(
        "широта",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        "долгота",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "геоточка (адрес + координаты)"
        verbose_name_plural = "геоточки (адреса с координатами)"

    def __str__(self):
        if self.latitude is not None and self.longitude is not None:
            return f"{self.address} ({self.latitude}, {self.longitude})"
        return f"{self.address} (координаты не определены)"
