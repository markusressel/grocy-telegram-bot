from typing import List

from pygrocy import Grocy
from pygrocy.grocy import Product

from grocy_telegram_bot.monitoring.watcher import GrocyEntityWatcher
from grocy_telegram_bot.stats import VOLATILE_STOCK_WATCHER_TIME, STOCK_WATCHER_TIME


class StockWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_update_listener, interval: float):
        super().__init__(grocy, on_update_listener, interval)

    def _fetch_data(self) -> List[Product]:
        items = self.grocy.stock()
        for i in items:
            i.get_details(self.grocy._api_client)

        return items

    @STOCK_WATCHER_TIME.time()
    def _run(self):
        super()._run()


class VolatileStockWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_update_listener, interval: float):
        super().__init__(grocy, on_update_listener, interval)

    def _fetch_data(self) -> List[Product]:
        missing = self.grocy.missing_products(True)
        expiring = self.grocy.expiring_products(True)
        expired = self.grocy.expired_products(True)
        return missing + expiring + expired

    @VOLATILE_STOCK_WATCHER_TIME.time()
    def _run(self):
        super()._run()
