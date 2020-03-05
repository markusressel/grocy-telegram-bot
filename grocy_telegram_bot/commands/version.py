from telegram import Update
from telegram.ext import Filters, CommandHandler, CallbackContext
from telegram_click.decorator import command

from grocy_telegram_bot.commands import GrocyCommandHandler
from grocy_telegram_bot.const import COMMAND_VERSION
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.util import send_message


class VersionCommandHandler(GrocyCommandHandler):

    def command_handlers(self):
        return [
            CommandHandler(COMMAND_VERSION,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._version_command_callback),
        ]

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
