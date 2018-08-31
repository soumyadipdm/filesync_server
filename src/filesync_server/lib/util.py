import logging


def setup_logging(log):
    """Set up logging"""
    log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    sh.setFormatter(formatter)
    log.addHandler(sh)


class Counter:
    """A simple counter to increase or decrease to/from

    :param value: initial value, defaults to zero
    """

    def __init__(self, value: int=0):
        self._counter = value

    def incr(self, increment: int=1):
        """Increase the counter value
        :param increment: value to increase counter with, defaults to 1
        """
        self._counter += increment

    def decr(self, decrement: int=1):
        """Decrease the counter value
        :param decrement: value to decrease counter with, defaults to 1
        """
        self._counter -= decrement

    @property
    def value(self):
        """Get the value of the counter"""
        return self._counter

    def __str__(self):
        return str(self._counter)
