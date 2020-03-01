from grocy_telegram_bot.util import fuzzy_match
from tests import TestBase


class FuzzyMatchTest(TestBase):

    def test_fuzzy_match(self):
        term = "new york jets"
        choices = ["Atlanta Falcons", "New York Jets", "New York Giants", "Dallas Cowboys"]

        matches = fuzzy_match(term, choices)

        self.assertIsNotNone(matches)
