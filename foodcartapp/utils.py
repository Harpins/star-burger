import requests

from django.db import transaction
from django.conf import settings
from .geocache import AddressCache

from geopy.distance import geodesic
import logging


logger = logging.getLogger(__name__)


def fetch_coordinates(address: str):
    
    if not address:
        logger.warning("Пустой адрес передан в fetch_coordinates")
        return None

    
    normalized_address = address.strip().lower()

    try:
        cached = AddressCache.objects.get(address__iexact=normalized_address)
        if cached.longitude is not None and cached.latitude is not None:
            logger.debug(
                f"Координаты из кэша: {address} → ({cached.longitude}, {cached.latitude})"
            )
            return float(cached.longitude), float(cached.latitude)
        else:
            logger.info(f"Адрес в кэше, но без координат: {address}, удаляем из кеша")
            cached.delete()
    except AddressCache.DoesNotExist:
        pass  

    base_url = "https://geocode-maps.yandex.ru/1.x"
    params = {
        "geocode": address, 
        "apikey": settings.YA_API_KEY,
        "format": "json",
    }

    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        found_places = data["response"]["GeoObjectCollection"]["featureMember"]

        if not found_places:
            logger.info(f"Яндекс не нашёл координаты для адреса: {address}")
            lon, lat = None, None
        else:
            lon_str, lat_str = found_places[0]["GeoObject"]["Point"]["pos"].split(" ")
            lon, lat = float(lon_str), float(lat_str)
            logger.debug(f"Яндекс нашёл: {address} → ({lon}, {lat})")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка сети при запросе к Яндексу: {e} | Адрес: {address}")
        lon, lat = None, None
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Ошибка парсинга ответа Яндекса: {e} | Адрес: {address}")
        lon, lat = None, None
    except Exception as e:
        logger.exception(
            f"Критическая ошибка в fetch_coordinates: {e} | Адрес: {address}"
        )
        lon, lat = None, None

    try:
        with transaction.atomic():
            AddressCache.objects.update_or_create(
                address=normalized_address,
                defaults={
                    "longitude": lon,
                    "latitude": lat,
                },
            )
    except Exception as e:
        logger.error(f"Не удалось сохранить координаты в кэш: {e}")
        
    coordinates = lon, lat if lon is not None and lat is not None else None

    return coordinates


def calculate_distance(lat1, lon1, lat2, lon2):
    return round(geodesic((lat1, lon1), (lat2, lon2)).km, 2)
