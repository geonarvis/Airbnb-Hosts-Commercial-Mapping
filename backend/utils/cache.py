from functools import lru_cache
import asyncio
from typing import Dict, Any
import json
from datetime import datetime

class CityDataCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._last_update: Dict[str, datetime] = {}
    
    async def get_or_set(self, city_name: str, getter_func, ttl_seconds: int = 3600):
        now = datetime.now()
        if (city_name in self._cache and 
            city_name in self._last_update and 
            (now - self._last_update[city_name]).seconds < ttl_seconds):
            return self._cache[city_name]
        
        data = await getter_func(city_name)
        self._cache[city_name] = data
        self._last_update[city_name] = now
        return data

city_cache = CityDataCache() 