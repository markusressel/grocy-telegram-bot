from collections import OrderedDict
from typing import Tuple, List, Dict

from pygrocy.grocy import ShoppingListProduct, Product
from telegram import Update, ParseMode, ReplyKeyboardRemove
from telegram.ext import Filters, CommandHandler, CallbackContext
from telegram_click.argument import Argument, Flag
from telegram_click.decorator import command

from grocy_telegram_bot.commands import GrocyCommandHandler
from grocy_telegram_bot.const import COMMAND_SHOPPING_LIST, COMMAND_SHOPPING, NEVER_EXPIRES_DATE, \
    COMMAND_SHOPPING_LIST_ADD
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.stats import COMMAND_TIME_SHOPPING_LIST, COMMAND_TIME_SHOPPING, COMMAND_TIME_SHOPPING_LIST_ADD
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
            CommandHandler(COMMAND_SHOPPING_LIST_ADD,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._shopping_list_add_callback),
        ]

    @command(
        name=COMMAND_SHOPPING_LIST_ADD,
        description="Add an item to a shopping list.",
        arguments=[
            Argument(name=["name"], description="Product name", example="Banana"),
            Argument(name=["amount"], description="Product amount", type=int, example="2",
                     validator=lambda x: x > 0, optional=True, default=1),
            Argument(name=["id"], description="Shopping list id", type=int, example="1",
                     optional=True, default=1),
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_SHOPPING_LIST_ADD.time()
    def _shopping_list_add_callback(self, update: Update, context: CallbackContext,
                                    name: str, amount: int, id: int) -> None:
        """
        Show a list of all shopping lists
        :param update: the chat update object
        :param context: telegram context
        :param name: product name
        :param amount: product amount
        :param id: shopping list id
        """

        products = self._grocy.get_all_products()
        self._reply_keyboard_handler.await_user_selection(
            update, context, name, choices=products, key=lambda x: x.name,
            callback=self._add_product_keyboard_response_callback,
            callback_data={
                "product_name": name,
                "amount": amount,
                "shopping_list_id": id
            }
        )

    def _add_product_keyboard_response_callback(self, update: Update, context: CallbackContext,
                                                product: Product, data: dict):
        """
        Called when the user has selected a product to add to a shopping list
        :param update: the chat update object
        :param context: telegram context
        :param product: the selected product
        :param data: callback data
        """
        bot = context.bot
        chat_id = update.effective_chat.id
        message_id = update.effective_message.message_id

        amount = data["amount"]
        shopping_list_id = data["shopping_list_id"]
        self._grocy.add_product_to_shopping_list(product.id, shopping_list_id, amount)

        text = "Added {}x {}".format(amount, product.name)
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_to=message_id,
                     menu=ReplyKeyboardRemove(selective=True))

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

        shopping_list_items = self._grocy.shopping_list(True)
        # TODO: sort by parent product / product category
        # TODO: let the user specify the order of product categories, according to the grocery store of his choice
        shopping_list_items = sorted(shopping_list_items, key=lambda x: x.product.name.lower())

        # generate message
        text = "*=> Shopping List <=*"
        # generate keyboard
        initial_button_tuples = self._create_shopping_list_item_button_tuples(shopping_list_items)
        inline_keyboard_items = self._create_shopping_list_keyboard_items(initial_button_tuples)
        inline_keyboard_markup = self._inline_keyboard_handler.build_inline_keyboard(inline_keyboard_items)

        # send message
        result = send_message(bot, chat_id, text, menu=inline_keyboard_markup, parse_mode=ParseMode.MARKDOWN)
        # register callback for button presses
        self._inline_keyboard_handler.register_listener(
            chat_id=chat_id,
            message_id=result.message_id,
            command_id=ShoppingListItemButtonCallbackData.command_id,
            callback=self._shopping_button_pressed_callback,
            callback_data={
                "shopping_list_items": shopping_list_items,
                "initial_keyboard_items": initial_button_tuples
            }
        )

    def _shopping_button_pressed_callback(self, update: Update, context: CallbackContext, button_data: str, data: Dict):
        button_data = ShoppingListItemButtonCallbackData.parse(button_data)
        query = update.callback_query
        query_id = query.id

        # TODO: Should this be a configuration option or a flag?
        #  if a flag should be used, this would need to be saved for every keyboard invididually...
        remove_finished_products_from_keyboard = True

        # TODO: there is currently no way to query shopping list ids, so this is hardcoded for now
        shopping_list_id = 1

        # retrieve shopping list from grocy
        # TODO: use list in store or from api?
        # shopping_list_items = self._grocy.shopping_list(True)
        shopping_list_items = data["shopping_list_items"]
        # find the matching item
        matching_items = list(filter(lambda x: x.id == button_data.shopping_list_item_id, shopping_list_items))
        if len(matching_items) <= 0:
            # if the item is not on the shopping list anymore, show a message
            context.bot.answer_callback_query(query_id, text=f"The item is not on the shopping list anymore.")
            # TODO: it should still be possible to add items beyond what the shopping list has
            #  if "remove_finished_products_from_keyboard" is False
            return

        # if the item is still on the shopping list, remove one item
        item = matching_items[0]
        response = self._grocy.remove_product_in_shopping_list(item.product_id, shopping_list_id, amount=1)
        if response is not None:
            response.raise_for_status()
        # also remove it from the keyboard
        stored_button_tuples = data["initial_keyboard_items"]
        # find the item in button tuples
        stored_item_title, stored_item_data = \
            list(filter(lambda x: x[1].shopping_list_item_id == item.id, stored_button_tuples.items()))[0]
        # increase its "clicked" counter
        stored_item_data.button_click_count += 1
        # generate the new button text
        stored_item_title_new = self._generate_button_title(item, stored_item_data)
        # remove the old key
        stored_button_tuples.pop(stored_item_title)
        if stored_item_data.button_click_count >= stored_item_data.shopping_list_amount and remove_finished_products_from_keyboard:
            # dont put the data back
            pass
        else:
            # put the modified data back in the dictionary
            stored_button_tuples[stored_item_title_new] = stored_item_data

        # add one item to the inventory
        product = item.product
        response = self._grocy.add_product(product_id=product.id, amount=1, price=None,
                                           best_before_date=NEVER_EXPIRES_DATE)
        if response is not None:
            response.raise_for_status()

        # regenerate keyboard
        keyboard_items = self._create_shopping_list_keyboard_items(stored_button_tuples)
        # we need to re-sort since the items have changed
        keyboard_items = OrderedDict(sorted(keyboard_items.items(), key=lambda x: x[0].lower()))
        inline_keyboard_markup = self._inline_keyboard_handler.build_inline_keyboard(keyboard_items)

        query.edit_message_reply_markup(reply_markup=inline_keyboard_markup)
        answer_text = f"Checked off '{product.name}' ({stored_item_data.button_click_count}/{stored_item_data.shopping_list_amount})"
        context.bot.answer_callback_query(query_id, text=answer_text)

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
    def _shopping_lists_callback(self, update: Update, context: CallbackContext,
                                 id: int, add_missing: bool or None) -> None:
        """
        Show a list of all shopping lists
        :param update: the chat update object
        :param context: telegram context
        :param id: shopping list id
        :param add_missing: whether to add missing products to the shopping list before displaying
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        if add_missing:
            self._grocy.add_missing_product_to_shopping_list(shopping_list_id=id)

        # TODO: when supported, pass shopping list id here
        shopping_list_items = self._grocy.shopping_list(True)
        shopping_list_items = sorted(shopping_list_items, key=lambda x: x.product.name.lower())

        item_texts = list(list(map(shopping_list_item_to_str, shopping_list_items)))
        text = "\n".join([
            "*=> Shopping List <=*",
            *item_texts,
        ]).strip()

        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)

    def _create_shopping_list_keyboard_items(self, items: Dict[str, ShoppingListItemButtonCallbackData]) -> Dict[
        str, str]:
        return OrderedDict(list(map(lambda x: (x[0], x[1].minify()), items.items())))

    def _create_shopping_list_item_button_tuples(self, items: List[ShoppingListProduct]) -> Dict[
        str, ShoppingListItemButtonCallbackData]:
        """
        Creates the data required for generating a keyboard button from shopping list items
        :param items: shopping list items
        :return : button title, button callback data
        """
        return OrderedDict(list(map(self._create_shopping_list_item_button_tuple, items)))

    def _create_shopping_list_item_button_tuple(self, item: ShoppingListProduct) -> Tuple[
        str, ShoppingListItemButtonCallbackData]:
        """
        Creates the data required for generating a keyboard button from a shopping list item
        :param item: shopping list item
        :return : button title, button callback data
        """
        button_data = self._create_shopping_list_item_button_data(item)
        button_title = self._generate_button_title(item, button_data)
        return button_title, button_data

    @staticmethod
    def _generate_button_title(item, stored_item_data) -> str:
        return f"{item.product.name} ({stored_item_data.button_click_count}/{int(item.amount)})"

    @staticmethod
    def _create_shopping_list_item_button_data(item: ShoppingListProduct,
                                               count: int = 0) -> ShoppingListItemButtonCallbackData:
        return ShoppingListItemButtonCallbackData(
            shopping_list_item_id=item.id,
            button_click_count=count,
            shopping_list_amount=int(item.amount)
        )
