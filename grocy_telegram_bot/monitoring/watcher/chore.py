from typing import List

from pygrocy import Grocy
from pygrocy.grocy import Chore

from grocy_telegram_bot.monitoring.watcher import GrocyEntityWatcher
from grocy_telegram_bot.stats import CHORE_WATCHER_TIME


class ChoreWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_update_listener, interval: float):
        super().__init__(grocy, on_update_listener, interval)

    def _fetch_data(self) -> List[Chore]:
        return self.grocy.chores(True)

    @CHORE_WATCHER_TIME.time()
    def _run(self):
        super()._run()
