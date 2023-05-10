import time
from typing import Optional

from ..logging import logger


class Timer(object):
    _nested = 0
    _id = 0

    def __init__(self, name: Optional[str] = None, verbose=1) -> None:
        self.name = name
        self.verbose = verbose
        self.start_time = time.time()
        self.end_time = 0

    @property
    def duration(self):
        return ((self.end_time or time.time()) - self.start_time) * 1000.0

    def stop(self):
        self.end_time = time.time()
        if self.verbose and self.name:
            duration = self.duration
            if duration > 1000:
                logger.debug(f"{self.current_padding()}{self.name} {duration / 1000:2.2f} sec")
            else:
                logger.debug(f"{self.current_padding()}{self.name} {duration:5.0f} ms")

    @classmethod
    def current_padding(cls):
        return max(0, Timer._nested) * '    '

    def __enter__(self):
        self.start_time = time.time()
        Timer._id += 1

        if self.verbose >= 2 and self.name:
            logger.debug(f"{self.current_padding()}{self.name}...")

        Timer._nested += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        Timer._nested -= 1
        self.stop()

        # task failed
        if exc_val:
            if self.verbose and self.name:
                logger.debug(f"{self.current_padding()}    {str(exc_val)}")
        return False


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        logger.info('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result

    return timed