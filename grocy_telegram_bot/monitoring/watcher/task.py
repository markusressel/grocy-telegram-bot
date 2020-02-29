from typing import List, Any

from pygrocy import Grocy

from grocy_telegram_bot.monitoring.watcher import GrocyEntityWatcher
from grocy_telegram_bot.stats import TASK_WATCHER_TIME


class TaskWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_update_listener, interval: float):
        super().__init__(grocy, on_update_listener, interval)

    def _fetch_data(self) -> List[Any]:
        # TODO: pygrocy doesn't support tasks yet
        return []

    @TASK_WATCHER_TIME.time()
    def _run(self):
        super()._run()
