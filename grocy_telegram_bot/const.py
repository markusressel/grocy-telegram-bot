from datetime import datetime

REQUESTS_TIMEOUT = (5, 5)
TELEGRAM_CAPTION_LENGTH_LIMIT = 200

NEVER_EXPIRES_DATE = datetime(year=2999, month=12, day=31).date()

# Commands
COMMAND_START = "start"
COMMAND_CHAT_ID = "chat_id"

COMMAND_INVENTORY = ["inventory", "i"]
COMMAND_INVENTORY_ADD = ["inventory_add", "ia"]
COMMAND_INVENTORY_REMOVE = ["inventory_remove", "ir"]
COMMAND_CHORES = ["chores", "ch"]
COMMAND_SHOPPING = ["shopping", "s"]
COMMAND_SHOPPING_LIST = ["shopping_list", "sl"]
COMMAND_SHOPPING_LIST_ADD = ["shopping_list_add", "sla"]

COMMAND_STATS = 'stats'

COMMAND_HELP = ['help', 'h']
COMMAND_VERSION = ['version', 'v']
COMMAND_CONFIG = ['config', 'c']

CANCEL_KEYBOARD_COMMAND = "/cancel_keyboard"
