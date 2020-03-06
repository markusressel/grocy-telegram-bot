import json
from typing import Dict

from grocy_telegram_bot.const import COMMAND_SHOPPING


class MinifiableData:

    def __init__(self, *args):
        self._minified_key_to_name = {}
        self._name_to_minified_key = {}

    @classmethod
    def parse(cls, text: str):
        minified_dict = json.loads(text)
        # create with random order first
        # noinspection PyArgumentList
        instance = cls(*minified_dict.values())
        # then generate minified key mapping
        instance._generate_minified_keys()
        # and reassign all properties
        for minified_key, name in instance._minified_key_to_name.items():
            vars(instance)[name] = minified_dict[minified_key]

        return instance

    def _get_properties(self):
        return dict(filter(lambda x: not x[0].startswith('_'), vars(self).items()))

    def minify(self) -> str:
        """
        Creates a minified json version of this object
        :return: minified json
        """
        self._generate_minified_keys()

        properties = self._get_properties()
        minified_dict = {}
        for name, minified_key in self._name_to_minified_key.items():
            minified_dict[minified_key] = properties[name]

        minified = self._json_minified(minified_dict)
        if len(minified) > 64:
            raise ValueError(f"Cant minify object, because it would still be to long: {self}")
        return minified

    @staticmethod
    def _json_minified(data: Dict) -> str:
        """
        Convert a dictionary to a minified json representation
        :param data: the data to convert
        :return: minified json string
        """
        return json.dumps(data, indent=None, separators=(',', ':'))

    def _generate_minified_keys(self):
        self._minified_key_to_name.clear()
        self._name_to_minified_key.clear()

        properties = self._get_properties()
        for name in properties.keys():
            max_len = len(name)
            length = 1
            while length <= max_len:
                minified_key = name[0:length]
                if minified_key in self._minified_key_to_name:
                    length += 1
                else:
                    self._minified_key_to_name[minified_key] = name
                    self._name_to_minified_key[name] = minified_key
                    break


class CallbackData(MinifiableData):
    command_id: str

    def __init__(self, *args):
        super().__init__(args)
        self.command_id = self.__class__.command_id


class ShoppingListItemButtonCallbackData(CallbackData):
    command_id: str = COMMAND_SHOPPING[1]

    def __init__(self, shopping_list_item_id: int, button_click_count: int, shopping_list_amount: int,
                 *args):
        super().__init__(args)
        self.shopping_list_item_id = shopping_list_item_id
        self.button_click_count = button_click_count
        self.shopping_list_amount = shopping_list_amount
