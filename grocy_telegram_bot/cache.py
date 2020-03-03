import logging

from expiringdict import ExpiringDict
from pygrocy import Grocy

from grocy_telegram_bot.config import Config

LOGGER = logging.getLogger(__name__)

CONFIG = Config()
# CACHE = LruCache(expires=CONFIG.GROCY_CACHE_DURATION.value.total_seconds(), concurrent=True)
CACHE = ExpiringDict(max_len=100, max_age_seconds=CONFIG.GROCY_CACHE_DURATION.value.total_seconds())

FUNCTIONS_TO_CACHE = [
    "Grocy.stock",
    "Grocy.volatile_stock",
    "Grocy.chore",
    "Grocy.chores",
    "Grocy.product",
    "Grocy.shopping_list",
    "Grocy.product_groups",
    "Grocy.get_userfields",
    "Grocy.get_last_db_changed",
    "Grocy.expired_products",
    "Grocy.expiring_products",
    "Grocy.missing_products",
]


def cache_decorator(func: classmethod):
    """
    Decorator to cache the result of a function call
    :param func: the function to wrap
    :return: wrapped function
    """

    def wrapper(*args, **kwargs):
        if not func.__qualname__.startswith("Grocy"):
            LOGGER.warning("Using cache on other object than Grocy, ignoring cache")
            return func(*args, **kwargs)

        if func.__qualname__ not in FUNCTIONS_TO_CACHE:
            LOGGER.debug("Clearing cache because of non-whitelisted function call")
            # clear existing cache since the data will probably change
            invalidate_cache()
            # don't cache if not whitelisted
            return func(*args, **kwargs)

        key = f"{func.__qualname__}_{args}_{kwargs}"

        if key in CACHE:
            return CACHE[key]

        response = func(*args, **kwargs)
        LOGGER.debug(f"Caching function response: {key}")
        CACHE[key] = response
        return response

    return wrapper


def invalidate_cache():
    """
    Removes all cached data
    """
    LOGGER.debug("Cleared cache")
    CACHE.clear()


class GrocyCached(Grocy):

    def __getattribute__(self, name):
        ret = super(Grocy, self).__getattribute__(name)
        if callable(ret):
            return cache_decorator(ret)
        else:
            return ret
