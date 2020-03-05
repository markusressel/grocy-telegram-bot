from telegram import Update, ParseMode
from telegram.ext import Filters, CommandHandler, CallbackContext
from telegram_click.decorator import command

from grocy_telegram_bot.commands import GrocyCommandHandler
from grocy_telegram_bot.const import COMMAND_SYSTEM
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.stats import COMMAND_TIME_SYSTEM
from grocy_telegram_bot.util import send_message


class SystemCommandHandler(GrocyCommandHandler):

    def command_handlers(self):
        return [
            CommandHandler(COMMAND_SYSTEM,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._system_info_callback),
        ]

    @command(
        name=COMMAND_SYSTEM,
        description="Show grocy system info.",
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_SYSTEM.time()
    def _system_info_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Show grocy system info
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        # TODO: pygrocy update
        system_info = self._grocy.shopping_list(True)

        text = "Not yet implemented"
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)
