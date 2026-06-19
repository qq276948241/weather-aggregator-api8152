from typing import Dict, List
from app.config import settings
from app.providers.base import WeatherProvider
from app.providers.mock_provider import MockWeatherProvider
from app.providers.openweathermap import OpenWeatherMapProvider
from app.providers.qweather import QWeatherProvider


_provider_map: Dict[str, type] = {
    "mock": MockWeatherProvider,
    "openweathermap": OpenWeatherMapProvider,
    "openweather": OpenWeatherMapProvider,
    "qweather": QWeatherProvider,
    "hefeng": QWeatherProvider,
}

_instances: Dict[str, WeatherProvider] = {}


def get_provider(name: str) -> WeatherProvider:
    if name not in _instances:
        cls = _provider_map.get(name.lower())
        if not cls:
            raise ValueError(f"Unknown weather provider: {name}")
        _instances[name] = cls()
    return _instances[name]


def get_available_providers() -> List[str]:
    return settings.provider_list


def get_all_providers() -> List[WeatherProvider]:
    result = []
    for name in get_available_providers():
        try:
            result.append(get_provider(name))
        except Exception:
            pass
    return result
