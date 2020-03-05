from telegram import Update, ParseMode
from telegram.ext import Filters, CommandHandler, CallbackContext
from telegram_click.decorator import command
from telegram_click.permission import PRIVATE_CHAT

from grocy_telegram_bot.commands import GrocyCommandHandler
from grocy_telegram_bot.const import COMMAND_CONFIG
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.util import send_message


class ConfigCommandHandler(GrocyCommandHandler):

    def command_handlers(self):
        return [
            CommandHandler(COMMAND_CONFIG,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._config_command_callback),
        ]

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
