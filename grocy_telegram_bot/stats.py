from prometheus_client import Summary, Gauge
from prometheus_client.metrics import MetricWrapperBase

from grocy_telegram_bot.const import *

COMMAND_TIME = Summary('command_processing_seconds', 'Time spent in a command handler', ['command'])
COMMAND_TIME_START = COMMAND_TIME.labels(command=COMMAND_START)
COMMAND_TIME_CHORES = COMMAND_TIME.labels(command=COMMAND_CHORES)
COMMAND_TIME_INVENTORY = COMMAND_TIME.labels(command=COMMAND_INVENTORY)
COMMAND_TIME_SHOPPING = COMMAND_TIME.labels(command=COMMAND_SHOPPING)
COMMAND_TIME_SHOPPING_LIST = COMMAND_TIME.labels(command=COMMAND_SHOPPING_LIST)
COMMAND_TIME_SHOPPING_LIST_ADD = COMMAND_TIME.labels(command=COMMAND_SHOPPING_LIST_ADD)

PRODUCT_INVENTORY_COUNT = Gauge(
    'product_inventory_count',
    'Number of inventory items per product name',
    ['product_name']
)

EXPIRED_PRODUCTS_COUNT = Gauge(
    'expired_products_count',
    'Number of expired products in inventory'
)

PRODUCTS_BELOW_MINIMUM_STOCK_COUNT = Gauge(
    'products_below_minimum_stock_count',
    'Number of items a product is below its minimum stock',
    ['product_name']
)

CHORES_COUNT = Gauge(
    'chores_count',
    'Number of overdue chores',
    ['type']
)

OVERDUE_CHORES_COUNT = CHORES_COUNT.labels(type="overdue")
TOTAL_CHORES_COUNT = CHORES_COUNT.labels(type="total")

SHOPPING_LIST_ITEM_COUNT = Gauge(
    'shopping_list_item_count',
    'Number items in a shopping list',
    ['name']
)

TASK_COUNT = Gauge(
    'task_count',
    'Number tasks',
)

WATCHER_TIME = Summary('watcher_processing_seconds', 'Time spent in a Watcher run', ['type'])

CHORE_WATCHER_TIME = WATCHER_TIME.labels(type="chore")
STOCK_WATCHER_TIME = WATCHER_TIME.labels(type="stock")
VOLATILE_STOCK_WATCHER_TIME = WATCHER_TIME.labels(type="volatile_stock")
SHOPPING_LIST_WATCHER_TIME = WATCHER_TIME.labels(type="shopping_list")
TASK_WATCHER_TIME = WATCHER_TIME.labels(type="task")


def get_metrics() -> []:
    entries = set()
    for name, obj in globals().items():
        if isinstance(obj, MetricWrapperBase):
            entries.add(obj)

    return list(entries)


def format_metrics() -> str:
    def format_sample(sample):
        result = "  "
        if len(sample[0]) > 0:
            result += str(sample[0])
        if len(sample[1]) > 0:
            result += str(sample[1])

        if len(result) > 0:
            result += " "
        result += str(sample[2])

        return result

    def format_samples(samples):
        return "\n".join(list(map(format_sample, samples)))

    def format_metric(metric):
        name = metric._name
        samples = list(metric._samples())
        samples_text = format_samples(samples)

        return "{}:\n{}".format(name, samples_text)

    return "\n\n".join(map(format_metric, get_metrics()))
