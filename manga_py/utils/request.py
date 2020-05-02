from collections import OrderedDict
from pathlib import Path
from typing import Union, Tuple, Optional

from cloudscraper import CloudScraper
from requests import Session, Response
from requests.adapters import HTTPAdapter
from requests.cookies import RequestsCookieJar
from requests.structures import CaseInsensitiveDict
from requests.utils import default_headers
from urllib.parse import urlparse

from .exceptions import CantWriteFileException

__all__ = ['Request', ]


class Request:
    _headers: CaseInsensitiveDict
    _session: Session

    def __init__(self, headers: dict):
        __headers = default_headers()
        __headers.update(headers)
        self._headers = __headers

        default_adapter = HTTPAdapter(max_retries=3)
        self._session = Session()
        self._session.adapters = OrderedDict({
            'http://': default_adapter,
            'https://': default_adapter,
        })

    def __del__(self):
        if self._session:
            self.close()
            self._session = None
            self._headers = None

    def close(self):
        self._session.close()

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, session: Session):
        self._session = session

    @property
    def headers(self) -> dict:
        return dict(self._headers.copy())

    @headers.setter
    def headers(self, headers: dict):
        self._headers = CaseInsensitiveDict(headers)

    def headers_update(self, headers: dict):
        self.headers.update(headers)

    @property
    def cookies(self) -> RequestsCookieJar:
        if not isinstance(self._session, Session):
            raise RuntimeError('Session error')
        return self._session.cookies

    @cookies.setter
    def cookies(self, cookies: dict):
        if not isinstance(self._session, Session):
            raise RuntimeError('Session error')
        c = self._session.cookies
        c.update(cookies)
        self._session.cookies = c

    def cookies_update(self, cookies: dict):
        if not isinstance(self._session, Session):
            raise RuntimeError('Session error')

        self._session.cookies.update(cookies)

    def __update_headers(self, headers: dict):
        _headers = self.headers.copy()
        _headers.update(headers)
        return _headers

    def request(self, method, url, has_referer: bool = True, **kwargs) -> Response:
        if not isinstance(self._session, Session):
            raise RuntimeError('Session error')

        if 'headers' in kwargs:
            headers = dict(kwargs.pop('headers'))
            kwargs['headers'] = self.__update_headers(headers)
        else:
            kwargs['headers'] = self.headers

        if not has_referer:
            kwargs.get('headers', {}).pop('Referer')

        with self._session.request(method, url, **kwargs) as response:
            return response

    def get(self, url: str, **kwargs) -> Response:
        kwargs.setdefault('allow_redirects', True)
        return self.request('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        return self.request('POST', url, **kwargs)

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
        return self._headers.get('User-Agent', None)

    @ua.setter
    def ua(self, user_agent: str):
        self._headers['User-Agent'] = user_agent

    def cf_scrape(self, url: str, **kwargs):
        kwargs.setdefault('browser', {'browser': 'chrome', 'mobile': False})
        tokens = CloudScraper.get_tokens(url, **kwargs)  # type: Tuple[dict, str]
        self.cookies_update(tokens[0])
        self.headers.update({'User-Agent': tokens[1]})
