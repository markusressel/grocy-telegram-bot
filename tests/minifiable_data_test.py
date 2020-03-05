from grocy_telegram_bot.telegram_util import ShoppingListItemButtonCallbackData
from tests import TestBase


class MinifiableDataTest(TestBase):

    def test_minifiable_data(self):
        callback_data = ShoppingListItemButtonCallbackData(
            product_id=123,
            button_click_count=0,
            shopping_list_amount=3
        )

        minified = callback_data.minify()
        self.assertEqual(minified, '{"c":"s","p":123,"b":0,"s":3}')

        parsed_callback_data = ShoppingListItemButtonCallbackData.parse(minified)
        self.assertEqual(list(vars(callback_data).values()), list(vars(parsed_callback_data).values()))
