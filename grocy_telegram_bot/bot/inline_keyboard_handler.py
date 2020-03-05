import logging

from telegram import Update
from telegram.ext import CallbackContext


class KeyboardHandler:
    # this map is used to map a command_id to a callback function
    _inline_keyboard__command_to_callback_map = {}

    # this map is used to remember what type is associated
    # with the callback data of a keyboard button
    _inline_keyboard__callback_data_type_map = {}

    def __init__(self):
        pass

    def register_listener(self, key: str, command_id: str, callback, callback_data: any):
        self._inline_keyboard__callback_data_type_map[key] = command_id
        self._inline_keyboard__command_to_callback_map[command_id] = {
            "callback": callback,
            "callback_data": callback_data
        }

    def inline_keyboard_click_callback(self, update: Update, context: CallbackContext):
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
            command_id = self._inline_keyboard__callback_data_type_map.get(f"{chat_id}_{message_id}", None)
            if command_id is None:
                bot.answer_callback_query(query_id, text="Unknown message")
                return

            callback_info = self._inline_keyboard__command_to_callback_map[command_id]
            callback = callback_info["callback"]
            callback_data = callback_info["callback_data"]
            # call listener
            callback(update, context, selection_data, callback_data)
        except Exception:
            logging.exception("Error processing inline keyboard button callback")
            bot.answer_callback_query(query_id, text="Error")
