import json
from typing import Dict

from grocy_telegram_bot.const import COMMAND_SHOPPING


class MinifiableData:
    _minified_key_to_name = {}
    _name_to_minified_key = {}

    @classmethod
    def parse(cls, text: str):
        minified_dict = json.loads(text)
        # create with random order first
        instance = cls(*minified_dict.values())
        # then generate minified key mapping
        instance._generate_minified_keys()
        # and reassign all properties
        for minified_key, name in instance._minified_key_to_name.items():
            vars(instance)[name] = minified_dict[minified_key]

        return instance

    def minify(self) -> str:
        """
        Creates a minified json version of this object
        :return: minified json
        """
        properties = vars(self)
        for name in properties.keys():
            max_len = len(name)
            length = 1
            while length <= max_len:
                minified_key = name[0:length]
                if minified_key in self._name_to_minified_key:
                    length += 1
                else:
                    self._name_to_minified_key[name] = minified_key
                    self._minified_key_to_name[minified_key] = name
                    break

        minified_dict = {}
        for name, minified_key in self._name_to_minified_key.items():
            minified_dict[minified_key] = properties[name]

        return self._json_minified(minified_dict)

    @staticmethod
    def _json_minified(data: Dict) -> str:
        """
        Convert a dictionary to a minified json representation
        :param data: the data to convert
        :return: minified json string
        """
        return json.dumps(data, indent=None, separators=(',', ':'))

    def _generate_minified_keys(self):
        properties = vars(self)
        for name in properties.keys():
            max_len = len(name)
            length = 1
            while length <= max_len:
                minified_key = name[0:length]
                if minified_key in self._name_to_minified_key:
                    length += 1
                else:
                    self._name_to_minified_key[name] = minified_key
                    self._minified_key_to_name[minified_key] = name
                    break


class CallbackData(MinifiableData):
    command_id: str


class ShoppingListItemButtonCallbackData(CallbackData):
    command_id: str = COMMAND_SHOPPING[1]

    def __init__(self, shopping_list_item_id: int, button_click_count: int, shopping_list_amount: int):
        super().__init__()
        self.shopping_list_item_id = shopping_list_item_id
        self.button_click_count = button_click_count
        self.shopping_list_amount = shopping_list_amount
