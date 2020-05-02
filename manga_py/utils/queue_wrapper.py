from queue import Queue
from threading import Thread

__all__ = ['QueueWrapper']


class QueueWrapper:
    __slots__ = ('_queue', 'max_threads')

    class Daemon(Thread):
        def __init__(self, queue):
            super().__init__()
            self.queue = queue

        def run(self):
            while True:
                callback, url, args, kwargs = self.queue.get()
                callback(url, *args, **kwargs)
                self.queue.task_done()

    def __init__(self, max_threads=4):
        self._queue = Queue()

        self.max_threads = max_threads

        for i in range(self.max_threads):
            t = self.Daemon(self._queue)
            t.setDaemon(True)
            t.start()

    @property
    def queue(self) -> Queue:
        return self._queue
