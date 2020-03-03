import logging
import threading
from typing import List

from pygrocy import Grocy

LOGGER = logging.getLogger(__name__)


class RegularIntervalWorker:
    """
    Base class for a worker that executes a specific task in a regular interval.
    """

    def __init__(self, interval: float):
        self._interval = interval
        self._timer = None

    def start(self):
        """
        Starts the worker
        """
        if self._timer is None:
            LOGGER.debug(f"Starting worker: {self.__class__.__name__}")
            self._schedule_next_run(0)
        else:
            LOGGER.debug("Already running, ignoring start() call")

    def stop(self):
        """
        Stops the worker
        """
        if self._timer is not None:
            self._timer.cancel()
        self._timer = None

    def _schedule_next_run(self, interval: int = None):
        """
        Schedules the next run
        """
        if self._timer is not None:
            self._timer.cancel()
        interval = interval if interval is not None else self._interval
        self._timer = threading.Timer(interval, self._worker_job)
        self._timer.start()

    def _worker_job(self):
        """
        The regularly executed task. Override this method.
        """
        try:
            self._run()
        except Exception as e:
            LOGGER.error(e, exc_info=True)
        finally:
            self._schedule_next_run()

    def _run(self):
        """
        The regularly executed task. Override this method.
        """
        raise NotImplementedError()


class GrocyEntityWatcher(RegularIntervalWorker):

    def __init__(self, grocy: Grocy, on_update_listener, interval: float):
        super().__init__(interval)
        self.grocy = grocy
        self.on_update_listener = on_update_listener
        self.data = None

    def _fetch_data(self) -> List:
        """
        Fetch the data this watcher should watch.
        """
        raise NotImplementedError()

    def _run(self):
        data = self._fetch_data()

        try:
            self.on_update_listener(self.data, data)
        finally:
            self.data = data
