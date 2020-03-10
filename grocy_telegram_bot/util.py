import functools
import hashlib
import logging
import operator
import os
from datetime import datetime, timezone, timedelta
from functools import wraps
from io import BytesIO
from time import time
from typing import List, Any, Tuple

from pygrocy.grocy import Chore, Product, ShoppingListProduct
from telegram import Bot, Message, ReplyMarkup

from grocy_telegram_bot.config import Config
from grocy_telegram_bot.const import TELEGRAM_CAPTION_LENGTH_LIMIT, NEVER_EXPIRES_DATE

LOGGER = logging.getLogger(__name__)

CONFIG = Config()


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        td = te - ts
        LOGGER.debug('func:%r took: %2.4f sec' % (f.__name__, td))
        return result

    return wrap


# def download_image_bytes(url: str) -> bytes:
#     """
#     Downloads the image from the given url
#     :return: the downloaded image
#     """
#     image = requests.get(url, timeout=REQUESTS_TIMEOUT)
#     image.raise_for_status()
#     return image.content

def flatten(data: List[List[Any]]) -> List[Any]:
    """
    Flattens a list of lists
    :param data: the data to flatten
    :return: flattened list
    """
    return functools.reduce(operator.iconcat, data, [])


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
    :param chat_id: the chat product_id to send the image to
    :param file_id: the telegram file product_id of the already uploaded image
    :param image_data: the image data
    :param caption: an optional image caption
    :return: a set of telegram image file_id's
    """
    if image_data is not None:
        image_bytes_io = BytesIO(image_data)
        image_bytes_io.name = 'image.jpeg'
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


def send_message(bot: Bot, chat_id: str, message: str, parse_mode: str = None, reply_to: int = None,
                 menu: ReplyMarkup = None) -> Message:
    """
    Sends a text message to the given chat
    :param bot: the bot
    :param chat_id: the chat product_id to send the message to
    :param message: the message to chat (may contain emoji aliases)
    :param parse_mode: specify whether to parse the text as markdown or HTML
    :param reply_to: the message product_id to reply to
    :param menu: inline keyboard menu markup
    """
    from emoji import emojize

    emojized_text = emojize(message, use_aliases=True)
    return bot.send_message(chat_id=chat_id, parse_mode=parse_mode, text=emojized_text, reply_to_message_id=reply_to,
                            reply_markup=menu)


def product_to_str(item: Product) -> str:
    from pygrocy.utils import parse_int
    amount = parse_int(item.available_amount, item.available_amount)

    text = f"{amount}x\t{item.name}"
    if item.best_before_date.date() < NEVER_EXPIRES_DATE:
        expire_date = datetime_fmt_date_only(item.best_before_date)
        text += f" (Exp: {expire_date})"

    return text


def chore_to_str(chore: Chore) -> str:
    """
    Converts a chore object into a string representation
    :param chore: the chore item
    :return: a text representation
    """
    today_utc_date_with_zero_time = datetime.today().astimezone(tz=timezone.utc)

    days_off = None
    date_str = None
    if chore.next_estimated_execution_time is not None:
        days_off = abs((chore.next_estimated_execution_time - today_utc_date_with_zero_time).days)
        date_str = datetime_fmt_date_only(chore.next_estimated_execution_time)

    lines = [chore.name]
    if days_off is not None:
        lines.append(f"  Due: {days_off} days ({date_str})")

    return "\n".join(lines)


def shopping_list_item_to_str(item: ShoppingListProduct) -> str:
    """
    Converts a shopping list item object into a string representation
    :param item: the shopping list item
    :return: a text representation
    """
    from pygrocy.utils import parse_int
    amount = parse_int(item.amount, item.amount)

    return f"{amount}x {item.product.name}"


def filter_overdue_chores(chores: List[Chore]) -> List[Chore]:
    today_utc_date_with_zero_time = datetime.today().astimezone(tz=timezone.utc)
    return list(filter(lambda x:
                       x.next_estimated_execution_time is not None
                       and x.next_estimated_execution_time <= today_utc_date_with_zero_time, chores))


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


def filter_new_by_key(a: List, b: List, key: callable) -> List:
    """
    Returns a list of all items, that are new in b when compared to a,
    using the key function to determine a unique identifier for list items
    :param a: "old" list
    :param b: "new" list
    :param key: function to map list items to a unique identifier
    :return: new list items
    """
    a_ids = set(map(key, a))
    b_ids = set(map(key, b))
    new_ids = b_ids - a_ids

    result = []
    for id in new_ids:
        item_in_b = list(filter(lambda x: key(x) == id, b))[0]
        result.append(item_in_b)
    return result


def fuzzy_match(term: str, choices: List[Any], limit: int = None, key=lambda x: x, ignorecase: bool = True) -> List[
    Tuple[Any, int]]:
    """
    Does a fuzzy search on the given
    :param term: the search term
    :param choices: list of possible choices
    :param key: function to turn a choice item into a string
    :param limit: Optional maximum for the number of elements returned
    :return: List of (choice, ratio) tuples, sorted by descending ratio
    """
    # map choices to key
    if ignorecase:
        term = term.casefold()
    choices = filter(lambda x: key(x) is not None, choices)
    key_map = dict(map(lambda x: (key(x).casefold() if ignorecase else key(x), x), choices))

    from fuzzywuzzy import process
    from fuzzywuzzy import fuzz
    matches = process.extract(term, key_map.keys(), limit=limit, scorer=fuzz.UWRatio)

    # map results back to original choices
    result = list(map(lambda x: (key_map[x[0]], x[1]), matches))

    return result
