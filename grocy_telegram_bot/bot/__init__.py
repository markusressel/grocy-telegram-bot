import logging
from datetime import timedelta
from typing import List, Tuple

from pygrocy.grocy import ShoppingListProduct
from telegram import Update, ParseMode, ReplyKeyboardRemove
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, \
    CallbackContext, CallbackQueryHandler
from telegram_click.argument import Argument, Flag
from telegram_click.decorator import command

from grocy_telegram_bot.cache import GrocyCached
from grocy_telegram_bot.commands import build_inline_keyboard
from grocy_telegram_bot.commands.chore import ChoreCommandHandler
from grocy_telegram_bot.commands.config import ConfigCommandHandler
from grocy_telegram_bot.commands.help import HelpCommandHandler
from grocy_telegram_bot.commands.inventory import InventoryCommandHandler
from grocy_telegram_bot.commands.stats import StatsCommandHandler
from grocy_telegram_bot.commands.version import VersionCommandHandler
from grocy_telegram_bot.config import Config
from grocy_telegram_bot.const import *
from grocy_telegram_bot.monitoring.monitor import Monitor
from grocy_telegram_bot.notifier import Notifier
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.stats import COMMAND_TIME_START, COMMAND_TIME_SHOPPING_LIST, \
    COMMAND_TIME_SHOPPING
from grocy_telegram_bot.telegram_util import ShoppingListItemButtonCallbackData
from grocy_telegram_bot.util import send_message, shopping_list_item_to_str, flatten

LOGGER = logging.getLogger(__name__)


class GrocyTelegramBot:
    """
    The main entry class of the grocy telegram bot
    """

    # this map is used to remember from which users we
    # are currently awaiting a response message
    awaiting_response = {}

    # this map is used to remember what type is associated
    # with the callback data of a keyboard button
    _inline_keyboard_callback_data_map = {}

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

        self._inline_handler_map = {
            ShoppingListItemButtonCallbackData.command_id: self._shopping_button_pressed_callback
        }

        self._updater = Updater(token=self._config.TELEGRAM_BOT_TOKEN.value, use_context=True)
        LOGGER.debug("Using bot id '{}' ({})".format(self._updater.bot.id, self._updater.bot.name))

        self._dispatcher = self._updater.dispatcher

        self._help_command_handler = HelpCommandHandler(self._config, self._grocy)
        self._grocy_command_handlers = [
            ChoreCommandHandler(self._config, self._grocy),
            ConfigCommandHandler(self._config, self._grocy),
            self._help_command_handler,
            InventoryCommandHandler(self._config, self._grocy),
            StatsCommandHandler(self._config, self._grocy),
            VersionCommandHandler(self._config, self._grocy)
        ]

        command_handlers = flatten(list(map(lambda x: x.command_handlers(), self._grocy_command_handlers)))

        handler_groups = {
            0: [CallbackQueryHandler(callback=self._inline_keyboard_click_callback)],
            1: command_handlers +
               [
                   CommandHandler(COMMAND_START,
                                  filters=(~ Filters.reply) & (~ Filters.forwarded),
                                  callback=self._start_callback),
                   CommandHandler(COMMAND_CHAT_ID,
                                  filters=(~ Filters.reply) & (~ Filters.forwarded),
                                  callback=self._chat_id_callback),

                   CommandHandler(COMMAND_SHOPPING,
                                  filters=(~ Filters.reply) & (~ Filters.forwarded),
                                  callback=self._shopping_callback),
                   CommandHandler(COMMAND_SHOPPING_LIST,
                                  filters=(~ Filters.reply) & (~ Filters.forwarded),
                                  callback=self._shopping_lists_callback),
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
        name=COMMAND_SHOPPING,
        description="Print shopping list with buttons to check off items.",
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_SHOPPING.time()
    def _shopping_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Show a list of all shopping lists
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        # TODO: maybe this should be a flag of /sl

        shopping_list_items = self._grocy.shopping_list(True)
        # TODO: sort by parent product / product category
        # TODO: let the user specify the order of product categories, according to the grocery store of his choice
        sorted(shopping_list_items, key=lambda x: x.product.name)

        item_texts = list(list(map(shopping_list_item_to_str, shopping_list_items)))
        text = "\n".join([
            "*=> Shopping List <=*",
            *item_texts,
        ]).strip()

        def create_item_tuple(item: ShoppingListProduct) -> Tuple[str, str]:
            button_title = f"{item.product.name} ({0}/{int(item.amount)})"
            callback_data = ShoppingListItemButtonCallbackData(
                shopping_list_item_id=item.id,
                button_click_count=0,
                shopping_list_amount=int(item.amount)
            )
            callback_data_str = callback_data.minify()
            return button_title, callback_data_str

        keyboard_items = dict(list(map(create_item_tuple, shopping_list_items)))
        inline_keyboard_markup = build_inline_keyboard(keyboard_items)

        result = send_message(bot, chat_id, text, menu=inline_keyboard_markup, parse_mode=ParseMode.MARKDOWN)
        self._inline_keyboard_callback_data_map[
            f"{chat_id}_{result.message_id}"] = ShoppingListItemButtonCallbackData.command_id

    def _shopping_button_pressed_callback(self, update: Update, context: CallbackContext, data: str):
        data = ShoppingListItemButtonCallbackData.parse(data)
        query_id = update.callback_query.id
        # TODO: add a product to inventory

        shopping_list_items = self._grocy.shopping_list(True)
        matching_items = list(filter(lambda x: x.id == data.shopping_list_item_id, shopping_list_items))

        shopping_list_item = matching_items[0]
        product = shopping_list_item.product

        self._grocy.add_product(product_id=product.id, amount=1, price=None, best_before_date=NEVER_EXPIRES_DATE)

        # TODO: this method is not feasible because it replies to a message, which we do not want
        #  since the only change should be in the keyboard items
        #  this whole class (bot) needs to be refactored into much more parts,
        #  possibly per topic (inventory, shopping, task, etc.)
        # self._inventory_add_execute()

        # TODO: regenerate menu_markup
        # menu_markup = self._build_inline_keyboard(vote_menu.items)
        # query.edit_message_reply_markup(reply_markup=menu_markup)

        context.bot.answer_callback_query(query_id, text='Added product to inventory')

    @command(
        name=COMMAND_SHOPPING_LIST,
        description="List shopping list items.",
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
            self._help_command_handler.help_command_callback(update, context)
            return

    def _inline_keyboard_click_callback(self, update: Update, context: CallbackContext):
        """
        Handles inline keyboard button click callbacks
        :param update:
        :param context:
        """
        bot = context.bot
        user_id = update.callback_query.from_user.id
        chat_id = update.effective_chat.id
        message_id = update.effective_message.message_id

        query = update.callback_query
        # TODO: is it possible to get this query_id when initially sending the keyboard? -> NOPE, but a chat_id & msg_id key should suffice
        # then it would be easy to remember the shopping list items in a dict somewhere
        # to regenerate it with the new counts/amounts
        query_id = query.id
        selection_data = query.data

        try:
            command_id = self._inline_keyboard_callback_data_map.get(f"{chat_id}_{message_id}", None)
            if command_id is None:
                bot.answer_callback_query(query_id, text="Unknown message")
                return

            self._inline_handler_map[command_id](update, context, selection_data)
        except Exception:
            logging.exception("Error processing inline keyboard button callback")
            bot.answer_callback_query(query_id, text="Error")

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
