from typing import List

from pygrocy import Grocy
from pygrocy.grocy import Chore, Product

from grocy_telegram_bot.monitoring.watcher.chore import ChoreWatcher
from grocy_telegram_bot.monitoring.watcher.inventory import ExpiredProductsWatcher, \
    ExpiringProductsWatcher
from grocy_telegram_bot.notifier import Notifier
from grocy_telegram_bot.util import product_to_str, chore_to_str


class Monitor:

    def __init__(self, notifier: Notifier, grocy: Grocy):
        self._notifier = notifier
        self._grocy = grocy

        self.watchers = [
            ChoreWatcher(self._grocy, self.on_chore_changed, 5),
            ExpiredProductsWatcher(self._grocy, self.on_expired_changed, 5),
            ExpiringProductsWatcher(self._grocy, self.on_expiring_changed, 5)
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
        old_ids = set(map(lambda x: x.chore_id, old))
        new_ids = set(map(lambda x: x.chore_id, new))

        new_overdue = new_ids - old_ids

        lines = []
        for item_id in new_overdue:
            chores = list(filter(lambda x: x.chore_id == item_id, new))[0]

            lines.append(chore_to_str(chores))

        if len(lines) > 0:
            message = "\n".join([
                "Chore(s) overdue:",
                *lines
            ])
            self._notifier.notify(message)

    def on_expired_changed(self, old: List[Product], new: List[Product]):
        old_ids = set(map(lambda x: x.product_id, old))
        new_ids = set(map(lambda x: x.product_id, new))

        new_expiring = new_ids - old_ids

        lines = []
        for item_id in new_expiring:
            product = list(filter(lambda x: x.product_id == item_id, new))[0]

            lines.append(product_to_str(product))

        if len(lines) > 0:
            message = "\n".join([
                "Product(s) expired:",
                *lines
            ])
            self._notifier.notify(message)

    def on_expiring_changed(self, old: List[Product], new: List[Product]):
        old_ids = set(map(lambda x: x.product_id, old))
        new_ids = set(map(lambda x: x.product_id, new))

        new_expiring = new_ids - old_ids

        lines = []
        for item_id in new_expiring:
            product = list(filter(lambda x: x.product_id == item_id, new))[0]

            lines.append(product_to_str(product))

        if len(lines) > 0:
            message = "\n".join([
                "Product(s) expiring soon:",
                *lines
            ])
            self._notifier.notify(message)
