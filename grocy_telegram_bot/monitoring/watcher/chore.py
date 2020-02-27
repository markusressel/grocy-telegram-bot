from typing import List

from pygrocy import Grocy
from pygrocy.grocy import Chore

from grocy_telegram_bot.monitoring.watcher import GrocyEntityWatcher
from grocy_telegram_bot.util import filter_overdue_chores


class OverdueChoreWatcher(GrocyEntityWatcher):

    def __init__(self, grocy: Grocy, on_change_listener, interval: float):
        super().__init__(grocy, on_change_listener, interval)

    def _fetch_data(self) -> List[Chore]:
        chores = self.grocy.chores(True)
        overdue = filter_overdue_chores(chores)
        return overdue
