from typing import List

from pygrocy import Grocy
from pygrocy.grocy import Product

from grocy_telegram_bot.monitoring.watcher import GrocyEntityWatcher


class StockWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_update_listener, interval: float):
        super().__init__(grocy, on_update_listener, interval)

    def _fetch_data(self) -> List[Product]:
        return self.grocy.stock(True)


class VolatileStockWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_update_listener, interval: float):
        super().__init__(grocy, on_update_listener, interval)

    def _fetch_data(self) -> List[Product]:
        # missing = self.grocy.missing_products(True)
        expiring = self.grocy.expiring_products(True)
        expired = self.grocy.expired_products(True)
        # return missing + expiring + expired
        return expiring + expired
