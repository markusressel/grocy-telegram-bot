from datetime import datetime, timedelta

from pygrocy.grocy import Product
from telegram import ParseMode, Update, ReplyKeyboardRemove
from telegram.ext import Filters, CommandHandler, CallbackContext
from telegram_click.argument import Flag, Argument
from telegram_click.decorator import command

from grocy_telegram_bot.commands import GrocyCommandHandler, build_reply_keyboard
from grocy_telegram_bot.const import COMMAND_INVENTORY, COMMAND_INVENTORY_ADD, NEVER_EXPIRES_DATE
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.stats import COMMAND_TIME_INVENTORY
from grocy_telegram_bot.util import send_message, product_to_str, fuzzy_match


class InventoryCommandHandler(GrocyCommandHandler):

    def command_handlers(self):
        return [
            CommandHandler(COMMAND_INVENTORY,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._inventory_callback),
            CommandHandler(COMMAND_INVENTORY_ADD,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._inventory_add_callback),
        ]

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
                     validator=lambda x: x > 0, optional=True, default=1),
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
                from dateutil import parser
                exp = parser.parse(exp)
            except:
                from pytimeparse import parse
                parsed = parse(exp)
                if parsed is None:
                    raise ValueError("Cannot parse the given time format: {}".format(exp))
                exp = datetime.now() + timedelta(seconds=parsed)

        products = self._grocy.get_all_products()
        matches = fuzzy_match(name, choices=products, key=lambda x: x.name, limit=5)

        perfect_matches = list(filter(lambda x: x[1] == 100, matches))
        if len(perfect_matches) != 1:
            keyboard_texts = list(map(lambda x: "{}".format(x[0].name), matches))
            keyboard = build_reply_keyboard(keyboard_texts)
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

        products = self._grocy.get_all_products()
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
        self._grocy.add_product(product_id=product.id, amount=amount, price=price, best_before_date=exp)

        text = "Added {}x {} (Exp: {}, Price: {})".format(
            amount, product.name, "Never" if exp == NEVER_EXPIRES_DATE else exp, price)
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_to=message_id,
                     menu=ReplyKeyboardRemove(selective=True))
