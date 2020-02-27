from typing import List

from pygrocy import Grocy
from pygrocy.grocy import Chore, Product

from grocy_telegram_bot.monitoring.watcher.chore import ChoreWatcher
from grocy_telegram_bot.monitoring.watcher.inventory import InventoryWatcher
from grocy_telegram_bot.notifier import Notifier


class Monitor:

    def __init__(self, notifier: Notifier, grocy: Grocy):
        self._notifier = notifier
        self._grocy = grocy

        self.watchers = [
            ChoreWatcher(self._grocy, self.on_chore_changed, 60),
            InventoryWatcher(self._grocy, self.on_inventory_changed, 60)
        ]

    def start(self):
        """
        Start monitoring the state of grocy.
        """
        for watcher in self.watchers:
            watcher.start()

    def stop(self):
        """
        Stop monitoring the state of grocy.
        """
        for watcher in self.watchers:
            watcher.stop()

    def on_chore_changed(self, old: List[Chore], new: List[Chore]):
        # TODO: send messages about new overdue chores
        self._notifier.notify("Chores updated!")

    def on_inventory_changed(self, old: List[Product], new: List[Product]):
        # TODO: send messages about expiring/expired products
        self._notifier.notify("Chores updated!")
