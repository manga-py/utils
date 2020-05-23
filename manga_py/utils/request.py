from collections import OrderedDict
from pathlib import Path
from typing import Union, Optional
from urllib.parse import urlparse

from cloudscraper import create_scraper
from requests import Session, Response
from requests.adapters import HTTPAdapter
from requests.structures import CaseInsensitiveDict
from requests.utils import default_headers

from .exceptions import CantWriteFileException

__all__ = ['Request', ]


class Request:
    __headers: CaseInsensitiveDict
    _session: Session
    __closed = False

    def __init__(self, headers: dict):
        __headers = default_headers()
        __headers.update(headers)
        self.__headers = __headers

        default_adapter = HTTPAdapter(max_retries=3)
        self._session = Session()
        self.session.headers = __headers
        self._session.adapters = OrderedDict({
            'http://': default_adapter,
            'https://': default_adapter,
        })

    def close(self, delete_headers=True):
        if isinstance(self._session, Session):
            self._session.close()
        self._session = None
        if delete_headers:
            self.__headers = None

    @property
    def session(self) -> Session:
        self.__assert_session()
        return self._session

    @session.setter
    def session(self, session: Session):
        self.close(False)

        if not isinstance(session, Session):
            raise RuntimeError('Session type error')

        self._session = session
        self._session.headers = self.__headers

    @property
    def headers(self) -> dict:
        self.__assert_session()
        return dict(self._session.headers.copy())

    @headers.setter
    def headers(self, headers: dict):
        self._session.headers = CaseInsensitiveDict(headers)

    def headers_update(self, headers: dict):
        self._session.headers.update(headers)

    @property
    def cookies(self) -> dict:
        if not isinstance(self._session, Session):
            raise RuntimeError('Session error')
        return self._session.cookies.get_dict()

    @cookies.setter
    def cookies(self, cookies: dict):
        if not isinstance(self._session, Session):
            raise RuntimeError('Session error')
        self._session.cookies.update(cookies)

    def cookies_update(self, cookies: dict):
        if not isinstance(self._session, Session):
            raise RuntimeError('Session error')

        self._session.cookies.update(cookies)

    def __update_headers(self, headers: dict):
        _headers = self.headers.copy()
        _headers.update(headers)
        return _headers

    def __assert_session(self):
        if self.__closed:
            raise RuntimeError('Session closed')

        if not isinstance(self._session, Session):
            raise RuntimeError('Session error')

    def request(self, method, url, **kwargs) -> Response:
        """
        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair.
        :param has_referer: (optional) if True, not not send Referer
        :rtype: requests.Response
        """
        self.__assert_session()

        if 'headers' in kwargs:
            headers = dict(kwargs.pop('headers'))
            kwargs['headers'] = self.__update_headers(headers)
        else:
            kwargs['headers'] = self.headers.copy()

        if not kwargs.pop('has_referer', True):
            kwargs.get('headers', {}).pop('Referer', None)

        with self._session.request(method, url, **kwargs) as response:
            return response

    def get(self, url: str, **kwargs) -> Response:
        kwargs.setdefault('allow_redirects', True)
        return self.request('GET', url, **kwargs)

    def post(self, url: str, data=None, **kwargs) -> Response:
        return self.request('POST', url, data=(data or {}), **kwargs)

    def download(self, url: str, path: Path, name: Union[str, Path] = None):
        """ path is directory """
        response = self.get(url)
        _path = path.resolve().joinpath(name or urlparse(response.url).path)

        with open(str(_path), 'wb') as w:
            if not w.writable():
                raise CantWriteFileException(str(_path))
            w.write(response.content)
        return _path

    @property
    def ua(self) -> Optional[str]:
        return self._session.headers.get('User-Agent', None)

    @ua.setter
    def ua(self, user_agent: str):
        self._session.headers['User-Agent'] = user_agent

    def cf_scrape(self, url: str, **kwargs):
        self.__assert_session()
        scrapper = create_scraper(
            sess=self.session
        )
        __headers = kwargs.pop('headers', {})
        __headers.update({
            "user-agent": self.ua
        })
        kwargs['headers'] = __headers

        tokens, ua = scrapper.get_tokens(url, **kwargs)  # type: dict, str

        self.cookies_update(tokens)

        if ua != self.ua:
            self.ua = ua
