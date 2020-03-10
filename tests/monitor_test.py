from pygrocy.grocy import Chore
from pygrocy.grocy_api_client import CurrentChoreResponse

from grocy_telegram_bot.util import filter_new_by_key
from tests import TestBase


class MonitorTest(TestBase):

    def test_filter_by_new_key_single_new(self):
        old = [
            Chore(CurrentChoreResponse(self._generate_chore_json(1))),
            Chore(CurrentChoreResponse(self._generate_chore_json(2))),
            Chore(CurrentChoreResponse(self._generate_chore_json(3)))
        ]

        new = [
            Chore(CurrentChoreResponse(self._generate_chore_json(4)))
        ]
        combined = old + new

        filtered = filter_new_by_key(old, combined, key=lambda x: x.id)

        self.assertEquals(len(filtered), 1)
        self.assertIn(new[0], filtered)

    def test_filter_by_new_key_new_and_removed_old(self):
        old = [
            Chore(CurrentChoreResponse(self._generate_chore_json(1))),
            Chore(CurrentChoreResponse(self._generate_chore_json(2))),
            Chore(CurrentChoreResponse(self._generate_chore_json(3)))
        ]

        new = [
            Chore(CurrentChoreResponse(self._generate_chore_json(1))),
            Chore(CurrentChoreResponse(self._generate_chore_json(2))),
            Chore(CurrentChoreResponse(self._generate_chore_json(4)))
        ]

        filtered = filter_new_by_key(old, new, key=lambda x: x.id)

        self.assertEquals(len(filtered), 1)
        self.assertIn(new[2], filtered)

    @staticmethod
    def _generate_chore_json(id: int) -> dict:
        return {
            "chore_id": id,
            "last_tracked_time": None,
            "next_estimated_execution_time": None
        }
