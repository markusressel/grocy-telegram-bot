import logging
from typing import List

from expiringdict import ExpiringDict
from pygrocy import Grocy
from pygrocy.grocy import Product

from grocy_telegram_bot.config import Config
from grocy_telegram_bot.util import timing

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
    "GrocyCached.get_all_products",
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
            LOGGER.debug(f"Clearing cache because of non-whitelisted function call: {func.__qualname__}")
            # clear existing cache since the data will probably change
            CACHE.clear()
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


class GrocyCached(Grocy):

    def __getattribute__(self, name):
        ret = super(Grocy, self).__getattribute__(name)
        if callable(ret):
            return cache_decorator(ret)
        else:
            return ret

    @timing
    def get_all_products(self) -> List[Product]:
        """
        Get a list of all products
        :return: produtcs
        """
        stock = self.stock(True)
        ex_stock = self.expiring_products(True)
        ex2_stock = self.expired_products(True)
        # TODO: add when fixed upstream
        # m_stock = self.missing_products(True)
        return stock + ex_stock + ex2_stock
