from typing import List

from pygrocy import Grocy
from pygrocy.grocy_api_client import ShoppingListItem

from grocy_telegram_bot.monitoring.watcher import GrocyEntityWatcher
from grocy_telegram_bot.stats import SHOPPING_LIST_WATCHER_TIME


class ShoppingListWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_update_listener, interval: float):
        super().__init__(grocy, on_update_listener, interval)

    def _fetch_data(self) -> List[ShoppingListItem]:
        return self.grocy.shopping_list(True)

    @SHOPPING_LIST_WATCHER_TIME.time()
    def _run(self):
        super()._run()
