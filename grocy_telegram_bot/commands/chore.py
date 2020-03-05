from datetime import datetime

from telegram import ParseMode, Update
from telegram.ext import Filters, CommandHandler, CallbackContext
from telegram_click.argument import Flag
from telegram_click.decorator import command

from grocy_telegram_bot.commands import GrocyCommandHandler
from grocy_telegram_bot.const import COMMAND_CHORES
from grocy_telegram_bot.permissions import CONFIG_ADMINS
from grocy_telegram_bot.stats import COMMAND_TIME_CHORES
from grocy_telegram_bot.util import send_message, filter_overdue_chores, chore_to_str


class ChoreCommandHandler(GrocyCommandHandler):

    def command_handlers(self):
        return [
            CommandHandler(COMMAND_CHORES,
                           filters=(~ Filters.reply) & (~ Filters.forwarded),
                           callback=self._chores_callback)
        ]

    @command(
        name=COMMAND_CHORES,
        description="List overdue chores.",
        arguments=[
            Flag(name=["all", "a"], description="Show all chores")
        ],
        permissions=CONFIG_ADMINS
    )
    @COMMAND_TIME_CHORES.time()
    def _chores_callback(self, update: Update, context: CallbackContext, all: bool) -> None:
        """
        Show a list of all chores
        :param update: the chat update object
        :param context: telegram context
        """
        bot = context.bot
        chat_id = update.effective_chat.id

        chores = self._grocy.chores(True)
        chores = sorted(
            chores,
            key=lambda
                x: datetime.now().astimezone() if x.next_estimated_execution_time is None else x.next_estimated_execution_time
        )

        overdue_chores = filter_overdue_chores(chores)
        other = [item for item in chores if item not in overdue_chores]

        overdue_item_texts = list(map(chore_to_str, overdue_chores))
        other_item_texts = list(map(chore_to_str, other))

        lines = ["*=> Chores <=*"]
        if all and len(other_item_texts) > 0:
            lines.extend([
                "",
                *other_item_texts
            ])

        if len(overdue_item_texts) > 0:
            lines.extend([
                "",
                "*Overdue:*",
                *overdue_item_texts
            ])

        text = "\n".join(lines).strip()
        send_message(bot, chat_id, text, parse_mode=ParseMode.MARKDOWN)
