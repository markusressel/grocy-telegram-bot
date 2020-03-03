import logging
from datetime import timedelta
from typing import List

from pygrocy.grocy import Product
from telegram import Update, ParseMode, ReplyMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, \
    CallbackContext
from telegram_click.argument import Argument, Flag
from telegram_click.decorator import command
from telegram_click.permission import PRIVATE_CHAT
from telegram_click.permission.base import Permission

from grocy_telegram_bot.cache import GrocyCached
from grocy_telegram_bot.config import Config
from grocy_telegram_bot.const import *
from grocy_telegram_bot.monitoring.monitor import Monitor
from grocy_telegram_bot.notifier import Notifier
from grocy_telegram_bot.stats import format_metrics, COMMAND_TIME_START, COMMAND_TIME_INVENTORY, COMMAND_TIME_CHORES, \
    COMMAND_TIME_SHOPPING_LIST
from grocy_telegram_bot.util import send_message, filter_overdue_chores, product_to_str, chore_to_str, \
    shopping_list_item_to_str, fuzzy_match

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


class _ConfigAdmins(Permission):

    def __init__(self):
        self._config = Config()

    def evaluate(self, update: Update, context: CallbackContext) -> bool:
        from_user = update.effective_message.from_user
        return from_user.username in self._config.TELEGRAM_ADMIN_USERNAMES.value


CONFIG_ADMINS = _ConfigAdmins()


class GrocyTelegramBot:
    """
    The main entry class of the grocy telegram bot
    """

    awaiting_response = {}

    def __init__(self, config: Config):
        """
        Creates an instance.
        :param config: configuration object
        """
        self._config = config

        self._grocy = GrocyCached(
            base_url=f"{config.GROCY_HOST.value}",
            api_key=config.GROCY_API_KEY.value,
            port=config.GROCY_PORT.value)

        self._updater = Updater(token=self._config.TELEGRAM_BOT_TOKEN.value, use_context=True)
        LOGGER.debug("Using bot id '{}' ({})".format(self._updater.bot.id, self._updater.bot.name))

        self._dispatcher = self._updater.dispatcher

        handler_groups = {
            0: [
                CommandHandler(COMMAND_START,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._start_callback),
                CommandHandler(COMMAND_CHAT_ID,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._chat_id_callback),
                CommandHandler(COMMAND_INVENTORY,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._inventory_callback),
                CommandHandler(COMMAND_INVENTORY_ADD,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._inventory_add_callback),

                CommandHandler(COMMAND_CHORES,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._chores_callback),
                CommandHandler(COMMAND_SHOPPING_LIST,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._shopping_lists_callback),
                CommandHandler(COMMAND_STATS,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._stats_callback),
                CommandHandler(COMMAND_VERSION,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._version_command_callback),
                CommandHandler(COMMAND_CONFIG,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._config_command_callback),
                CommandHandler(COMMAND_COMMANDS,
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._commands_command_callback),
                CommandHandler(CANCEL_KEYBOARD_COMMAND[1:],
                               filters=(~ Filters.reply) & (~ Filters.forwarded),
                               callback=self._cancel_keyboard_callback),
                # unknown command handler
                MessageHandler(
                    filters=Filters.command & (~ Filters.forwarded),
                    callback=self._unknown_command_callback),
                MessageHandler(
                    filters=(~ Filters.forwarded),
                    callback=self._any_message_callback),
            ]
        }

        for group, handlers in handler_groups.items():
            for handler in handlers:
                self._updater.dispatcher.add_handler(handler, group=group)

        self._monitor = None
        chat_ids = self._config.NOTIFICATION_CHAT_IDS.value
        if chat_ids is not None and len(chat_ids) > 0:
            self._notifier = Notifier(self._updater, chat_ids)
            interval = self._config.GROCY_CACHE_DURATION.value + timedelta(seconds=1)
            self._monitor = Monitor(interval, self._notifier, self._grocy)

    @property
    def bot(self):
        return self._updater.bot

    def start(self):
        """
        Starts up the bot.
        """
        if self._monitor is not None:
            self._monitor.start()
        self._updater.start_polling()
        self._updater.idle()

    def stop(self):
        """
        Shuts down the bot.
        """
        if self._monitor is not None:
            self._monitor.stop()
        self._updater.stop()

    @COMMAND_TIME_START.time()
    def _start_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Welcomes a new user with a greeting message
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id
        user_first_name = update.effective_user.first_name

        if not CONFIG_ADMINS.evaluate(update, context):
            send_message(bot, chat_id, "Sorry, you do not have permissions to use this bot.")
            return

        send_message(bot, chat_id,
                     f"Welcome {user_first_name},\nthis is your grocy-telegram-bot instance, ready to go!")

    @command(
        name=COMMAND_CHAT_ID,
        description="Show current chat id.",
        permissions=CONFIG_ADMINS
    )
    def _chat_id_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Print the current chat id, to make it easier to add it to notifications
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id
        send_message(bot, chat_id, f"{chat_id}", parse_mode=ParseMode.MARKDOWN)

    @command(
        name=COMMAND_CHORES,
        description="List overdue chores.",
        arguments=[
            Flag(name=["all", "a"], description="Show all chores")
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_CHORES.time()
    def _chores_callback(self, update: Update, context: CallbackContext, all: bool) -> None:
        """
        Show a list of all chores
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        chores = self._grocy.chores(True)
        chores = sorted(chores, key=lambda x: x.next_estimated_execution_time)

        overdue_chores = filter_overdue_chores(chores)
        other = [item for item in chores if item not in overdue_chores]

        overdue_item_texts = list(map(chore_to_str, overdue_chores))
        other_item_texts = list(map(chore_to_str, other))

        lines = ["*=> Chores <=*"]
        if all and len(other_item_texts) > 0:
            lines.extend([
                "",
                *other_item_texts
            ])

        if len(overdue_item_texts) > 0:
            lines.extend([
                "",
                "*Overdue:*",
                *overdue_item_texts
            ])

        text = "\n".join(lines).strip()
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)

    @command(
        name=COMMAND_INVENTORY,
        description="List product inventory.",
        arguments=[
            Flag(name=["missing", "m"], description="Show missing products"),
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_INVENTORY.time()
    def _inventory_callback(self, update: Update, context: CallbackContext, missing: bool) -> None:
        """
        Show a list of all products in the inventory
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        # if missing:
        #     # TODO: bugged in pygrocy
        #     products = self._grocy.missing_products(True)
        # else:
        products = self._grocy.stock(True)

        products = sorted(products, key=lambda x: x.name.lower())

        item_texts = list(list(map(product_to_str, products)))
        text = "\n".join([
            "*=> Inventory <=*",
            *item_texts,
        ]).strip()

        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)

    @command(
        name=COMMAND_INVENTORY_ADD,
        description="Add a product to inventory.",
        arguments=[
            Argument(name=["name"], description="Product name", example="Banana"),
            Argument(name=["amount"], description="Product amount", type=int, example="2",
                     validator=lambda x: x > 0),
            Argument(name=["exp"], description="Expiration date or duration", example="20.01.2020",
                     optional=True, default="Never"),
            Argument(name=["price"], description="Product price", type=float, example="2.80",
                     validator=lambda x: x > 0, optional=True),
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_INVENTORY.time()
    def _inventory_add_callback(self, update: Update, context: CallbackContext,
                                name: str, amount: int, exp: str, price: float or None) -> None:
        """
        Add a product to the inventory
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id
        message_id = update.effective_message.message_id
        user_id = update.effective_user.id

        # parse the expiration date input
        if exp.casefold() == "never".casefold():
            exp = NEVER_EXPIRES_DATE
        else:
            try:
                import dateutil
                exp = dateutil.parser.parse(exp)
            except:
                from pytimeparse import parse
                parsed = parse(exp)
                if parsed is None:
                    raise ValueError("Cannot parse the given time format: {}".format(exp))
                exp = datetime.now() + timedelta(seconds=parsed)

        products = self._get_all_products()
        matches = fuzzy_match(name, choices=products, key=lambda x: x.name, limit=5)

        perfect_matches = list(filter(lambda x: x[1] == 100, matches))
        if len(perfect_matches) != 1:
            keyboard_texts = list(map(lambda x: "{}".format(x[0].name), matches))
            keyboard = self._build_reply_keyboard(keyboard_texts)
            text = "No unique perfect match found, please select one of the menu options"
            self.await_response(user_id, keyboard_texts,
                                ok_callback=self._add_product_keyboard_response_callback,
                                callback_data={
                                    "product_name": name,
                                    "amount": amount,
                                    "exp": exp,
                                    "price": price
                                })
            send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_to=message_id, menu=keyboard)
            return

        product = matches[0][0]
        self._inventory_add_execute(update, context, product, amount, exp, price)

    def _add_product_keyboard_response_callback(self, update: Update, context: CallbackContext, message: str,
                                                data: dict):
        """
        This method is called when a user selects an entry from a keyboard, after
        a failed attempt to specify an exact product name
        :param update: the chat update object
        :param context: telegram context
        :param message: the selected keyboard entry
        :param data: callback data
        """
        product_name = message
        amount = data["amount"]
        exp = data["exp"]
        price = data["price"]

        products = self._get_all_products()
        product = list(filter(lambda x: x.name == product_name, products))[0]
        self._inventory_add_execute(update, context, product, amount, exp, price)

    def _inventory_add_execute(self, update: Update, context: CallbackContext, product: Product, amount: int,
                               exp: datetime, price: float):
        """
        Adds a product to the inventory
        :param update: the chat update object
        :param context: telegram context
        :param product: product entity
        :param amount: amount
        :param exp: expiration date
        :param price: price
        """
        bot = context.bot
        chat_id = update.effective_chat.id
        message_id = update.effective_message.message_id
        self._grocy.add_product(product_id=product.product_id, amount=amount, price=price, best_before_date=exp)

        text = "Added {}x {} (Exp: {}, Price: {})".format(
            amount, product.name, "Never" if exp == NEVER_EXPIRES_DATE else exp, price)
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_to=message_id,
                     menu=ReplyKeyboardRemove(selective=True))

    def _cancel_keyboard_callback(self, update: Update, context: CallbackContext):
        bot = context.bot
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        message_id = update.effective_message.message_id

        text = "Cancelled"
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_to=message_id,
                     menu=ReplyKeyboardRemove(selective=True))

        if user_id in self.awaiting_response:
            self.awaiting_response.pop(user_id)

    @command(
        name=COMMAND_SHOPPING_LIST,
        description="List shopping lists.",
        arguments=[
            Argument(name=["id"], description="Shopping list id", type=int, example="1",
                     optional=True, default=1),
            Flag(name=["add_missing", "a"],
                 description="Add items below minimum stock to the shopping list")
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_SHOPPING_LIST.time()
    def _shopping_lists_callback(self, update: Update, context: CallbackContext, id: int,
                                 add_missing: bool or None) -> None:
        """
        Show a list of all shopping lists
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        if add_missing:
            self._grocy.add_missing_product_to_shopping_list(shopping_list_id=id)

        # TODO: when supported, pass shopping list id here
        shopping_list_items = self._grocy.shopping_list(True)
        shopping_list_items = sorted(shopping_list_items, key=lambda x: x.product.name)

        item_texts = list(list(map(shopping_list_item_to_str, shopping_list_items)))
        text = "\n".join([
            "*=> Shopping List <=*",
            *item_texts,
        ]).strip()

        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)

    @command(
        name=COMMAND_STATS,
        description="List statistics of this bot.",
        permissions=CONFIG_ADMINS
    )
    def _stats_callback(self, update: Update, context: CallbackContext) -> None:
        """
        /stats command handler
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        message = update.effective_message
        chat_id = update.effective_chat.id

        text = format_metrics()

        send_message(bot, chat_id, text, reply_to=message.message_id)

    @command(
        name=COMMAND_VERSION,
        description="Show the version of this bot.",
        permissions=CONFIG_ADMINS
    )
    def _version_command_callback(self, update: Update, context: CallbackContext) -> None:
        """
        /stats command handler
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        message = update.effective_message
        chat_id = update.effective_chat.id

        from grocy_telegram_bot import __version__
        text = "{}".format(__version__)
        send_message(bot, chat_id, text, reply_to=message.message_id)

    @command(
        name=COMMAND_CONFIG,
        description="Show current application configuration.",
        permissions=PRIVATE_CHAT & CONFIG_ADMINS
    )
    def _config_command_callback(self, update: Update, context: CallbackContext):
        """
        /config command handler
        :param update: the chat update object
        :param context: telegram context
        """
        from container_app_conf.formatter.toml import TomlFormatter

        bot = context.bot
        chat_id = update.effective_message.chat_id
        message_id = update.effective_message.message_id

        text = self._config.print(formatter=TomlFormatter())
        text = "```\n{}\n```".format(text)
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_to=message_id)

    @command(
        name=COMMAND_COMMANDS,
        description="List commands supported by this bot.",
        permissions=CONFIG_ADMINS
    )
    def _commands_command_callback(self, update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat_id = update.effective_chat.id

        from telegram_click import generate_command_list
        text = generate_command_list(update, context)
        send_message(bot, chat_id, text,
                     parse_mode=ParseMode.MARKDOWN,
                     reply_to=message.message_id)

    def _unknown_command_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Handles unknown commands send by a user
        :param update: the chat update object
        :param context: telegram context
        """
        message = update.effective_message
        username = "N/A"
        if update.effective_user is not None:
            username = update.effective_user.username

        user_is_admin = username in self._config.TELEGRAM_ADMIN_USERNAMES.value
        if user_is_admin:
            self._commands_command_callback(update, context)
            return

    def _any_message_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Used to respond to response keyboard entry selections
        :param update: the chat update object
        :param context: telegram context
        """
        user_id = update.effective_user.id
        text = update.effective_message.text

        if user_id not in self.awaiting_response:
            return

        data = self.awaiting_response[user_id]
        if text in data["valid_responses"]:
            LOGGER.debug("Awaited response from user {} received: {}".format(user_id, text))
            try:
                data["ok_callback"](update, context, text, data["callback_data"])
                self.awaiting_response.pop(user_id)
            finally:
                # TODO: log error
                pass

    @staticmethod
    def _build_reply_keyboard(items: List[str]) -> ReplyMarkup:
        """
        Builds a menu to select an item from a list
        :param items: list of items to choose from
        :return: reply markup
        """
        items.append(CANCEL_KEYBOARD_COMMAND)
        keyboard = list(map(lambda x: KeyboardButton(x), items))
        # NOTE: the "selective=True" requires the menu to be sent as a reply
        # (or with an @username mention)
        return ReplyKeyboardMarkup.from_column(keyboard, one_time_keyboard=True, selective=True)

    def await_response(self, user_id: str, options: List[str], callback_data: dict, ok_callback):
        """
        Remember, that we are awaiting a response message from a user
        :param user_id: the user id
        :param options: a list of messages that the user can send as a valid response
        """
        if user_id in self.awaiting_response:
            raise AssertionError("Already awaiting response to a previous query from user {}".format(user_id))

        self.awaiting_response[user_id] = {
            "valid_responses": options,
            "ok_callback": ok_callback,
            "callback_data": callback_data
        }

    def _get_all_products(self) -> List[Product]:
        stock = self._grocy.stock(True)
        ex_stock = self._grocy.expiring_products(True)
        ex2_stock = self._grocy.expired_products(True)
        # TODO: add when fixed upstream
        # m_stock = self._grocy.missing_products(True)
        return stock + ex_stock + ex2_stock
