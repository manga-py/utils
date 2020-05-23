import time
import unittest
from pathlib import Path
from sys import platform

from requests import get, Session

from manga_py.utils import sanitize_full_path, sanitize_filename
from manga_py.utils.html_parser import HtmlParser
from manga_py.utils.multi_requests_wrapper import MultiRequestsWrapper
from manga_py.utils.request import Request

is_win = platform == 'win32'
heroku = 'http://httpbin-sttv.herokuapp.com'


class TestArchive(unittest.TestCase):
    def test_download(self):
        threads = 8
        num_bytes = 100

        download_wrapper = MultiRequestsWrapper(threads)

        start_time = time.time()
        urls = [
            f'{heroku}/drip?numbytes={num_bytes}&code=200&delay=1'
        ] * threads

        _ = []

        def download_fn(url: str, *args, **kwargs):
            _.append(len(get(url).content))

        download_wrapper.run(download_fn, urls)

        self.assertGreater(threads, time.time() - start_time)
        self.assertEqual(threads * num_bytes, sum(_))

    def test_sanitize(self):
        filename = r'disallowed/p:%^*:at\h'

        path_one = Path('.')
        path_two = Path('.').joinpath('more-path/path/here')
        path_three = Path('.').joinpath(filename)

        if is_win:
            path_three_resolved = Path('.').joinpath('disallowed/p_%^__at/h').resolve()
            filename_sanitized = 'disallowed_p_%^__at_h'
        else:
            path_three_resolved = Path('.').joinpath(filename).resolve()
            filename_sanitized = r'disallowed_p:%^*:at\h'

        self.assertEqual(path_one.resolve(), sanitize_full_path(path_one))
        self.assertEqual(path_two.resolve(), sanitize_full_path(path_two))
        self.assertEqual(path_three_resolved, sanitize_full_path(path_three))

        self.assertEqual(filename_sanitized, sanitize_filename(filename))

    def test_html_parser(self):
        selector = '#background-image'
        content = get(heroku).text  # type: str

        elements = HtmlParser.parse(content)
        one_element = HtmlParser.select_one(elements, selector, 0)
        sections = HtmlParser.select(elements, 'section')
        classes = HtmlParser.extract_attribute(sections, 'class')

        _text = HtmlParser.select_one(elements, '.markdown b', 0)
        text = HtmlParser.text(_text)
        text_without_strip = HtmlParser.text(_text, False)

        _title = HtmlParser.select_one(elements, '.title', 0)
        title_text = HtmlParser.text(_title)
        text_full = HtmlParser.text_full(_title)

        self.assertEqual(elements.cssselect(selector)[0], one_element)
        self.assertEqual('/static/image.jpg', HtmlParser.background_image(one_element))
        for cls in classes:
            self.assertLess(1, len(cls))
        self.assertEqual('Run locally:', text)
        self.assertEqual('Run locally: ', text_without_strip)
        self.assertEqual('httpbin.org', title_text)
        self.assertEqual("""httpbin.org
____________________________________
________________________________________0.9.2""".replace('_', ' '), text_full)

    def test_request(self):
        ua = 'Py-Test-User-Agent-%d' % time.time()
        req = Request({})
        url = f'{heroku}/get'

        self.assertEqual(
            get(url).json()['headers'],
            req.get(url).json()['headers']
        )

        _h = f'{ua}/123'
        self.assertEqual(
            _h,
            req.get(url, headers={'my-header': _h}, has_referer=False).json()['headers']['My-Header']
        )

        req.ua = ua

        self.assertEqual(ua, req.ua)

        with req.get(f'{heroku}/cookies') as r:
            cookies = r.json()['cookies']

        self.assertEqual(req.cookies, cookies)
        self.assertEqual({}, cookies)

        with req.get(f'{heroku}/cookies/set?manga-py=2.0') as r:
            pass

        with req.get(f'{heroku}/cookies') as r:
            cookies = r.json()['cookies']

        self.assertEqual(req.cookies, cookies)
        self.assertEqual({
            'manga-py': '2.0'
        }, cookies)

        old_session = req.session
        new_session = Session()
        req.session = new_session

        self.assertNotEqual(old_session, req.session)
        self.assertEqual(new_session, req.session)

        old_headers = req.headers
        new_ua = 'NewUserAgent'
        new_headers = {
            'usEr-aGeNt': new_ua
        }
        req.headers = new_headers

        self.assertNotEqual(old_headers, req.headers)
        self.assertEqual(new_headers, req.headers)

        self.assertEqual(new_ua, req.get(f'{heroku}/get').json()['headers']['User-Agent'])

        req.headers_update({'user-agent': ua})

        self.assertEqual(ua, req.ua)

        post = req.post(f'{heroku}/post', data={'my-data': ua})

        self.assertEqual(ua, post.json()['form']['my-data'])

        req.close()
        self.assertRaises(RuntimeError, req.get, heroku)

    def test_request_bad_session(self):
        req = Request({})

        req._session = {}

        self.assertRaises(RuntimeError, lambda x: req.cookies, 0)

        def assert_set_session():
            req.session = {}

        self.assertRaises(RuntimeError, assert_set_session)

        req.close()

        self.assertRaises(RuntimeError, lambda x: req.session, 0)

    @staticmethod
    def _cf_req():
        req = Request({})
        req.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        return req


if __name__ == '__main__':
    unittest.main()
