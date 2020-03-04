import logging
from typing import List

from telegram import Update, ParseMode, ReplyKeyboardRemove
from telegram.ext import CallbackContext

from grocy_telegram_bot.util import send_message

LOGGER = logging.getLogger(__name__)


class ResponseHandler:
    # this map is used to remember from which users we
    # are currently awaiting a response message
    awaiting_response = {}

    def __init__(self):
        pass

    def on_message(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        text = update.effective_message.text

        if user_id not in self.awaiting_response:
            return

        data = self.awaiting_response[user_id]
        if text in data["valid_responses"]:
            LOGGER.debug("Awaited response from user {} received: {}".format(user_id, text))
            try:
                data["callback"](update, context, text, data["callback_data"])
                self.awaiting_response.pop(user_id)
            finally:
                # TODO: log error
                pass

    def await_response(self, user_id: str, options: List[str], callback_data: dict, callback):
        """
        Remember, that we are awaiting a response message from a user
        :param user_id: the user id
        :param options: a list of messages that the user can send as a valid response
        :param callback: function to call with callback data
        :param callback_data: data to pass to callback
        """
        if user_id in self.awaiting_response:
            raise AssertionError("Already awaiting response to a previous query from user {}".format(user_id))

        self.awaiting_response[user_id] = {
            "valid_responses": options,
            "callback": callback,
            "callback_data": callback_data
        }

    def cancel_keyboard_callback(self, update: Update, context: CallbackContext):
        bot = context.bot
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        message_id = update.effective_message.message_id

        text = "Cancelled"
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_to=message_id,
                     menu=ReplyKeyboardRemove(selective=True))

        if user_id in self.awaiting_response:
            self.awaiting_response.pop(user_id)
