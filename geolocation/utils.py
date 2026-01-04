import requests
import logging
from django.db import transaction
from django.conf import settings
from geopy.distance import geodesic

from .models import Location 

logger = logging.getLogger(__name__)


def fetch_coordinates(address: str):
    
    if not address:
        logger.warning("Пустой адрес передан в fetch_coordinates")
        return None

    address = address.strip()
    if not address:
        return None

    try:
        location = Location.objects.get(address__iexact=address)
        if location.latitude is not None and location.longitude is not None:
            logger.debug(f"Координаты из Location: {address} → ({location.longitude}, {location.latitude})")
            return float(location.longitude), float(location.latitude)
        else:
            logger.info(f"Location существует, но без координат: {address}")
    except Location.DoesNotExist:
        location = None

    base_url = "https://geocode-maps.yandex.ru/1.x"
    params = {
        "geocode": address,
        "apikey": settings.YA_API_KEY,
        "format": "json",
    }

    lon, lat = None, None
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        feature_member = data["response"]["GeoObjectCollection"]["featureMember"]
        if not feature_member:
            logger.info(f"Яндекс ничего не нашёл по адресу: {address}")
        else:
            coords_str = feature_member[0]["GeoObject"]["Point"]["pos"]
            lon_str, lat_str = coords_str.split()
            lon, lat = float(lon_str), float(lat_str)
            logger.debug(f"Яндекс вернул координаты: {address} → ({lon}, {lat})")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка сети при геокодировании адреса '{address}': {e}")
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Ошибка парсинга ответа Яндекса для адреса '{address}': {e}")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при геокодировании адреса '{address}': {e}")

    try:
        with transaction.atomic():
            obj, created = Location.objects.update_or_create(
                address__iexact=address,
                defaults={
                    "address": address, 
                    "longitude": lon,
                    "latitude": lat,
                }
            )
            if created:
                logger.info(f"Создана новая Location: {address}")
            else:
                logger.info(f"Обновлена Location: {address}")
    except Exception as e:
        logger.error(f"Ошибка сохранения Location для адреса '{address}': {e}")

    if lon is not None and lat is not None:
        return lon, lat
    else:
        return None


def calculate_distance(coord1: tuple, coord2: tuple) -> float | None:
    if None in (coord1, coord2) or coord1 is None or coord2 is None:
        return None
    try:
        return round(geodesic(coord1, coord2).kilometers, 2)
    except Exception:
        return None
