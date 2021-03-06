import logging
import os
import sys

from container_app_conf.formatter.toml import TomlFormatter
from prometheus_client import start_http_server

from grocy_telegram_bot.bot import GrocyTelegramBot
from grocy_telegram_bot.config import Config

parent_dir = os.path.abspath(os.path.join(os.path.abspath(__file__), "..", ".."))
sys.path.append(parent_dir)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


def main():
    config = Config()

    log_level = logging._nameToLevel.get(str(config.LOG_LEVEL.value).upper(), config.LOG_LEVEL.default)
    logging.getLogger("grocy_telegram_bot").setLevel(log_level)

    LOGGER.debug("Config:\n{}".format(config.print(TomlFormatter())))

    # start prometheus server
    if config.STATS_ENABLED.value:
        start_http_server(config.STATS_PORT.value)

    grocy_telegram_bot = GrocyTelegramBot(config)
    grocy_telegram_bot.start()


if __name__ == '__main__':
    main()
