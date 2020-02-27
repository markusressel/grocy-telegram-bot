from typing import List

from pygrocy import Grocy
from pygrocy.grocy import Product

from grocy_telegram_bot.monitoring.watcher import GrocyEntityWatcher


class ExpiredProductsWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_change_listener, interval: float):
        super().__init__(grocy, on_change_listener, interval)

    def _fetch_data(self) -> List[Product]:
        return self.grocy.expired_products(True)


class ExpiringProductsWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_change_listener, interval: float):
        super().__init__(grocy, on_change_listener, interval)

    def _fetch_data(self) -> List[Product]:
        return self.grocy.expiring_products(True)
