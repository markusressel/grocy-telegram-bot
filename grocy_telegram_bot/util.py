import hashlib
import logging
import os
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import List

from emoji import emojize
from pygrocy.grocy import Chore, Product
from telegram import Bot

from grocy_telegram_bot.config import Config
from grocy_telegram_bot.const import TELEGRAM_CAPTION_LENGTH_LIMIT

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

CONFIG = Config()


# def download_image_bytes(url: str) -> bytes:
#     """
#     Downloads the image from the given url
#     :return: the downloaded image
#     """
#     image = requests.get(url, timeout=REQUESTS_TIMEOUT)
#     image.raise_for_status()
#     return image.content


def create_hash(data: bytes) -> str:
    """
    Creates a hash of the given bytes
    :param data: data to hash
    :return: hash
    """
    return hashlib.md5(data).hexdigest()


def cryptographic_hash(data: bytes or str) -> str:
    """
    Creates a cryptographic hash of the given bytes
    :param data: data to hash
    :return: hash
    """
    if isinstance(data, str):
        data = data.encode()
    import hashlib
    hash = hashlib.sha512(data).hexdigest()
    return hash


def send_photo(bot: Bot, chat_id: str, file_id: int or None = None, image_data: bytes or None = None,
               caption: str = None) -> [str]:
    """
    Sends a photo to the given chat
    :param bot: the bot
    :param chat_id: the chat id to send the image to
    :param file_id: the telegram file id of the already uploaded image
    :param image_data: the image data
    :param caption: an optional image caption
    :return: a set of telegram image file_id's
    """
    if image_data is not None:
        image_bytes_io = BytesIO(image_data)
        image_bytes_io.name = 'inspireme.jpeg'
        photo = image_bytes_io
    elif file_id is not None:
        photo = file_id
    else:
        raise ValueError("At least one of file_id and image_data has to be provided!")

    if caption is not None:
        caption = _format_caption(caption)

    message = bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
    return set(map(lambda x: x.file_id, message.photo))


def format_for_single_line_log(text: str) -> str:
    """
    Formats a text for log
    :param text:
    :return:
    """
    text = "" if text is None else text
    return " ".join(text.split())


def _format_caption(text: str) -> str or None:
    if text is None:
        return None

    # remove empty lines
    text = os.linesep.join([s for s in text.splitlines() if s.strip()])
    # limit to 200 characters (telegram api limitation)
    if len(text) > TELEGRAM_CAPTION_LENGTH_LIMIT:
        text = text[:197] + "…"

    return text


def datetime_fmt_date_only(d: datetime):
    from babel.dates import format_date
    time = d.astimezone()
    return format_date(time.date(), locale=CONFIG.LOCALE.value)


def send_message(bot: Bot, chat_id: str, message: str, parse_mode: str = None, reply_to: int = None):
    """
    Sends a text message to the given chat
    :param bot: the bot
    :param chat_id: the chat id to send the message to
    :param message: the message to chat (may contain emoji aliases)
    :param parse_mode: specify whether to parse the text as markdown or HTML
    :param reply_to: the message id to reply to
    """
    emojized_text = emojize(message, use_aliases=True)
    bot.send_message(chat_id=chat_id, parse_mode=parse_mode, text=emojized_text, reply_to_message_id=reply_to)


def product_to_str(item: Product) -> str:
    from pygrocy.utils import parse_int
    amount = parse_int(item.available_amount, item.available_amount)

    text = f"{amount}x\t{item.name}"
    if item.best_before_date < datetime(year=2999, month=12, day=31).astimezone(tz=timezone.utc):
        expire_date = datetime_fmt_date_only(item.best_before_date)
        text += f" (Exp: {expire_date})"

    return text


def chore_to_str(chore: Chore) -> str:
    """
    Converts a chore object into a string representation suitable for a telegram chat
    :param chore: the chore item
    :return: a text representation
    """
    today_utc_date_with_zero_time = datetime.today().astimezone(tz=timezone.utc)
    days_off = abs((chore.next_estimated_execution_time - today_utc_date_with_zero_time).days)
    date_str = datetime_fmt_date_only(chore.next_estimated_execution_time)

    return "\n".join([
        chore.name,
        f"  Due: {days_off} days ({date_str})"
    ])


def filter_overdue_chores(chores: List[Chore]) -> List[Chore]:
    today_utc_date_with_zero_time = datetime.today().astimezone(tz=timezone.utc)
    return list(filter(lambda x: x.next_estimated_execution_time <= today_utc_date_with_zero_time, chores))


def filter_has_expiry_products(products: List[Product]):
    never_expires_date = datetime(year=2999, month=12, day=31).astimezone(tz=timezone.utc)
    return list(filter(lambda x: x.best_before_date < never_expires_date, products))


def filter_expiring_products(products: List[Product], days_to_expiry: int = 5):
    today_minus_expiry_timeframe = datetime.today().astimezone(tz=timezone.utc) - timedelta(days=days_to_expiry)
    products_with_expiry = filter_has_expiry_products(products)
    return list(filter(lambda x: x.best_before_date < today_minus_expiry_timeframe, products_with_expiry))


def filter_expired_products(products: List[Product]):
    date_today = datetime.today().astimezone(tz=timezone.utc)
    products_with_expiry = filter_has_expiry_products(products)
    return list(filter(lambda x: x.best_before_date < date_today, products_with_expiry))
