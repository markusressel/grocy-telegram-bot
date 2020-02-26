import hashlib
import logging
import os
from io import BytesIO

from emoji import emojize
from telegram import Bot

from grocy_telegram_bot.const import TELEGRAM_CAPTION_LENGTH_LIMIT

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


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