import logging
import os
import sys

from container_app_conf.formatter.toml import TomlFormatter

from grocy_telegram_bot.bot import GrocyTelegramBot
from grocy_telegram_bot.config import Config

parent_dir = os.path.abspath(os.path.join(os.path.abspath(__file__), "..", ".."))
sys.path.append(parent_dir)

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

if __name__ == '__main__':
    config = Config()

    LOGGER.debug("Config:\n{}".format(config.print(TomlFormatter())))

    # start prometheus server
    # start_http_server(config.STATS_PORT.value)

    grocy_telegram_bot = GrocyTelegramBot(config)
    grocy_telegram_bot.start()
