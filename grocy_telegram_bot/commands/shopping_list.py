from typing import Tuple

from pygrocy.grocy import ShoppingListProduct
from telegram import Update, ParseMode
from telegram.ext import Filters, CommandHandler, CallbackContext
from telegram_click.argument import Argument, Flag
from telegram_click.decorator import command

from grocy_telegram_bot.commands import GrocyCommandHandler, build_inline_keyboard
from grocy_telegram_bot.const import COMMAND_SHOPPING_LIST, COMMAND_SHOPPING, NEVER_EXPIRES_DATE
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.stats import COMMAND_TIME_SHOPPING_LIST, COMMAND_TIME_SHOPPING
from grocy_telegram_bot.telegram_util import ShoppingListItemButtonCallbackData
from grocy_telegram_bot.util import send_message, shopping_list_item_to_str


class ShoppingListCommandHandler(GrocyCommandHandler):

    def command_handlers(self):
        return [
            CommandHandler(COMMAND_SHOPPING,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._shopping_callback),
            CommandHandler(COMMAND_SHOPPING_LIST,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._shopping_lists_callback),
        ]

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
        self._keyboard_handler.register_listener(
            f"{chat_id}_{result.message_id}",
            ShoppingListItemButtonCallbackData.command_id,
            self._shopping_button_pressed_callback
        )

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
