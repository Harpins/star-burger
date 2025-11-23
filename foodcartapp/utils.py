import requests

from geopy.distance import geodesic
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def fetch_coordinates(address):
    if not address:
        logger.warning("Пустой адрес передан в fetch_coordinates")
        return None

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
            return None

        most_relevant = found_places[0]
        lon, lat = most_relevant["GeoObject"]["Point"]["pos"].split(" ")

        logger.debug(f"Успешно геокодирован адрес '{address}' → ({lon}, {lat})")
        return float(lon), float(lat)

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к Яндекс.Геокодеру: {e} | Адрес: {address}")
        return None
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Ошибка парсинга ответа Яндекса для адреса '{address}': {e}")
        return None
    except Exception as e:
        logger.exception(
            f"Неизвестная ошибка в fetch_coordinates для адреса '{address}': {e}"
        )
        return None


def calculate_distance(lat1, lon1, lat2, lon2):
    return round(geodesic((lat1, lon1), (lat2, lon2)).km, 2)
