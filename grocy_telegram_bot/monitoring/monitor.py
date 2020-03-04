from datetime import timedelta
from typing import List, Any

from pygrocy import Grocy
from pygrocy.grocy import Chore, Product
from pygrocy.grocy_api_client import ShoppingListItem

from grocy_telegram_bot.monitoring.watcher.chore import ChoreWatcher
from grocy_telegram_bot.monitoring.watcher.inventory import StockWatcher, VolatileStockWatcher
from grocy_telegram_bot.monitoring.watcher.shopping_list import ShoppingListWatcher
from grocy_telegram_bot.monitoring.watcher.task import TaskWatcher
from grocy_telegram_bot.notifier import Notifier
from grocy_telegram_bot.stats import TOTAL_CHORES_COUNT, OVERDUE_CHORES_COUNT, PRODUCT_INVENTORY_COUNT, \
    EXPIRED_PRODUCTS_COUNT, SHOPPING_LIST_ITEM_COUNT, TASK_COUNT
from grocy_telegram_bot.util import product_to_str, chore_to_str, filter_overdue_chores, filter_expired_products, \
    filter_expiring_products, filter_new_by_key


class Monitor:

    def __init__(self, interval: timedelta, notifier: Notifier, grocy: Grocy):
        self._notifier = notifier
        self._grocy = grocy

        interval_seconds = interval.total_seconds()

        self.watchers = [
            ChoreWatcher(self._grocy, self.on_chore_update, interval_seconds),
            StockWatcher(self._grocy, self.on_stock_update, interval_seconds),
            VolatileStockWatcher(self._grocy, self.on_volatile_stock_update, interval_seconds),
            ShoppingListWatcher(self._grocy, self.on_shopping_list_update, interval_seconds),
            TaskWatcher(self._grocy, self.on_task_update, interval_seconds)
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

    def on_chore_update(self, old: List[Chore], new: List[Chore]):
        TOTAL_CHORES_COUNT.set(len(new))

        new_overdue = filter_overdue_chores(new)
        OVERDUE_CHORES_COUNT.set(len(new_overdue))

        if old is not None:
            old_overdue = filter_overdue_chores(old)
            self._notify_about_new_overdue_chores(old_overdue, new_overdue)

    def _notify_about_new_overdue_chores(self, old: List[Chore], new: List[Chore]):
        # check if a new chore is due
        new_overdue = filter_new_by_key(old, new, key=lambda x: x.id)

        lines = list(map(chore_to_str, new_overdue))
        # send notification if required
        if len(lines) > 0:
            message = "\n".join([
                "Chore(s) overdue:",
                *lines
            ])
            self._notifier.notify(message)

    def on_stock_update(self, old: List[Product], new: List[Product]):
        for product in new:
            PRODUCT_INVENTORY_COUNT.labels(product_name=product.name).set(product.available_amount)

    def on_volatile_stock_update(self, old: List[Product], new: List[Product]):
        for product in new:
            PRODUCT_INVENTORY_COUNT.labels(product_name=product.name).set(product.available_amount)

        new_expired = filter_expired_products(new)
        EXPIRED_PRODUCTS_COUNT.set(len(new_expired))

        if old is not None:
            old_expired = filter_expired_products(old)
            self._notify_about_new_expired_products(old_expired, new_expired)

            old_expiring = filter_expiring_products(old)
            new_expiring = filter_expiring_products(new)
            self._notify_about_new_expired_products(old_expiring, new_expiring)

    def _notify_about_new_expiring_products(self, old: List[Product], new: List[Product]):
        new_expiring = filter_new_by_key(old, new, key=lambda x: x.id)

        lines = list(map(product_to_str, new_expiring))
        if len(lines) > 0:
            message = "\n".join([
                "Product(s) expiring soon:",
                *lines
            ])
            self._notifier.notify(message)

    def _notify_about_new_expired_products(self, old: List[Product], new: List[Product]):
        new_expired = filter_new_by_key(old, new, key=lambda x: x.id)

        lines = list(map(product_to_str, new_expired))
        if len(lines) > 0:
            message = "\n".join([
                "Product(s) expired:",
                *lines
            ])
            self._notifier.notify(message)

    def on_shopping_list_update(self, old: List[ShoppingListItem], new: List[ShoppingListItem]):
        # TODO: when pygrocy supports multiple shopping lists, this has to be updated
        SHOPPING_LIST_ITEM_COUNT.labels(name="Shopping List").set(len(new))

    def on_task_update(self, old: List[Any], new: List[Any]):
        TASK_COUNT.set(len(new))
