from typing import List

from pygrocy import Grocy

from grocy_telegram_bot.monitoring.watcher import GrocyEntityWatcher


class InventoryWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_change_listener, interval: float):
        super().__init__(grocy, on_change_listener, interval)

    def _fetch_data(self) -> List:
        return self.grocy.stock(True)
