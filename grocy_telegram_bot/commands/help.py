from telegram import Update, ParseMode
from telegram.ext import Filters, CommandHandler, CallbackContext
from telegram_click.decorator import command

from grocy_telegram_bot.commands import GrocyCommandHandler
from grocy_telegram_bot.const import COMMAND_HELP
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.util import send_message


class HelpCommandHandler(GrocyCommandHandler):

    def command_handlers(self):
        return [
            CommandHandler(COMMAND_HELP,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self.help_command_callback),
        ]

    @command(
        name=COMMAND_HELP,
        description="List commands supported by this bot.",
        permissions=CONFIG_ADMINS,
    )
    def help_command_callback(self, update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat_id = update.effective_chat.id

        from telegram_click import generate_command_list
        text = generate_command_list(update, context)
        send_message(bot, chat_id, text,
                     parse_mode=ParseMode.MARKDOWN,
                     reply_to=message.message_id)
