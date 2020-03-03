import logging
import re

from container_app_conf import ConfigBase
from container_app_conf.entry.bool import BoolConfigEntry
from container_app_conf.entry.int import IntConfigEntry
from container_app_conf.entry.list import ListConfigEntry
from container_app_conf.entry.string import StringConfigEntry
from container_app_conf.entry.timedelta import TimeDeltaConfigEntry
from container_app_conf.source.env_source import EnvSource
from container_app_conf.source.toml_source import TomlSource
from container_app_conf.source.yaml_source import YamlSource
from py_range_parse import Range

NODE_MAIN = "grocy_telegram_bot"

NODE_NOTIFICATION = "notification"
NODE_TELEGRAM = "telegram"

NODE_GROCY = "grocy"
NODE_HOST = "host"
NODE_API_KEY = "api_key"

NODE_STATS = "stats"
NODE_ENABLED = "enabled"
NODE_PORT = "port"


class Config(ConfigBase):

    def __new__(cls, *args, **kwargs):
        yaml_source = YamlSource("grocy_telegram_bot")
        toml_source = TomlSource("grocy_telegram_bot")
        data_sources = [
            EnvSource(),
            yaml_source,
            toml_source
        ]
        return super(Config, cls).__new__(cls, data_sources=data_sources)

    LOG_LEVEL = StringConfigEntry(
        description="Log level",
        key_path=[
            NODE_MAIN,
            "log_level"
        ],
        regex=re.compile(f" {'|'.join(logging._nameToLevel.keys())}", flags=re.IGNORECASE),
        default="WARNING",
    )

    LOCALE = StringConfigEntry(
        description="Bot Locale",
        key_path=[
            NODE_MAIN,
            "locale"
        ],
        default="en",
    )

    TELEGRAM_BOT_TOKEN = StringConfigEntry(
        description="The telegram bot token to use",
        key_path=[
            NODE_MAIN,
            NODE_TELEGRAM,
            "bot_token"
        ],
        example="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        secret=True)

    TELEGRAM_ADMIN_USERNAMES = ListConfigEntry(
        item_type=StringConfigEntry,
        key_path=[
            NODE_MAIN,
            NODE_TELEGRAM,
            "admin_usernames"
        ],
        required=True,
        example=[
            "myadminuser",
            "myotheradminuser"
        ]
    )

    GROCY_CACHE_DURATION = TimeDeltaConfigEntry(
        description="Duration to cache Grocy REST api call responses",
        key_path=[
            NODE_MAIN,
            NODE_GROCY,
            "cache_duration"
        ],
        required=True,
        default="60s",
    )

    NOTIFICATION_CHAT_IDS = ListConfigEntry(
        item_type=StringConfigEntry,
        key_path=[
            NODE_MAIN,
            NODE_NOTIFICATION,
            "chat_ids"
        ],
        default=[]
    )

    GROCY_HOST = StringConfigEntry(
        description="Hostname of the Grocy instance",
        key_path=[
            NODE_MAIN,
            NODE_GROCY,
            NODE_HOST
        ],
        required=True,
        default="127.0.0.1"
    )

    GROCY_PORT = IntConfigEntry(
        description="Port of the Grocy REST api",
        key_path=[
            NODE_MAIN,
            NODE_GROCY,
            NODE_PORT
        ],
        range=Range(1, 65535),
        default=80
    )

    GROCY_API_KEY = StringConfigEntry(
        description="Grocy API Key used for REST authentication",
        key_path=[
            NODE_MAIN,
            NODE_GROCY,
            NODE_API_KEY
        ],
        required=True,
        example="abcdefgh12345678",
        secret=True
    )

    STATS_ENABLED = BoolConfigEntry(
        description="Whether to enable prometheus statistics or not.",
        key_path=[
            NODE_MAIN,
            NODE_STATS,
            NODE_ENABLED
        ],
        default=True
    )

    STATS_PORT = IntConfigEntry(
        description="The port to expose statistics on.",
        key_path=[
            NODE_MAIN,
            NODE_STATS,
            NODE_PORT
        ],
        default=8000
    )
