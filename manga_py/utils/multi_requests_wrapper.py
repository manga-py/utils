from typing import Callable, Iterable

from .queue_wrapper import QueueWrapper

__all__ = ['MultiRequestsWrapper']


class MultiRequestsWrapper(QueueWrapper):

    def run(self, callback: Callable, urls: Iterable, *args, **kwargs):
        """
        callback: Callable
        def download_fn(url: str, *args, **kwargs):
            url == 'http://site/path/to/image.png'
            _idx == 0  # increment
            pass

        dl = Downloader()
        dl.download(download_fn, 'http://site/path/to/image.png')
        """
        for idx, url in enumerate(urls):
            temp_kwargs = kwargs.copy()
            temp_kwargs.update(_idx=idx)
            self.queue.put((callback, url, args, temp_kwargs))
        self.queue.join()
