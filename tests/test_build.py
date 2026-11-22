from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

from test_page import PageParser
from tools.build_site import ROOT, build_site
from tools.preview_site import PagesHandler
from tools.site_routes import ROUTES


class QuietPagesHandler(PagesHandler):
    def log_message(self, format, *args):
        pass


class PagesBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory(prefix="dyuym-test-build-")
        cls.output = Path(cls.temp.name)
        build_site(cls.output)
        handler = partial(QuietPagesHandler, directory=cls.temp.name)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()
        cls.temp.cleanup()

    def built_target(self, path):
        path = unquote(path)
        if path == "/":
            return self.output / "index.html"
        target = self.output / path.lstrip("/")
        if target.is_file():
            return target
        if target.is_dir():
            return target / "index.html"
        return target.with_name(target.name + ".html")

    def test_aliases_and_legacy_paths_are_built_from_the_same_sources(self):
        self.assertEqual(ROUTES["/главная"], "index.html")
        self.assertEqual(ROUTES["/медиасобытия/волга-юнпресс"], "journals/volga-yunpress.html")
        self.assertEqual(ROUTES["/media-camp"], "journals/media-camp.html")
        for route, source in ROUTES.items():
            with self.subTest(route=route):
                self.assertTrue(route.startswith("/"))
                self.assertFalse(route.endswith("/"))
                self.assertFalse(route.endswith(".html"))
                original = (ROOT / source).read_bytes()
                self.assertEqual((self.output / source).read_bytes(), original)
                self.assertEqual(self.built_target(route).read_bytes(), original)
        self.assertTrue((self.output / ".nojekyll").is_file())

    def test_pretty_urls_are_direct_html_responses(self):
        for route in ROUTES:
            with self.subTest(route=route):
                url = self.base + quote(route, safe="/") + "?preview=1"
                with urlopen(url, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.geturl(), url)  # no redirect or added slash
                    self.assertEqual(response.headers.get_content_type(), "text/html")
                    html = response.read().decode("utf-8")
                    self.assertIn(f'https://www.cdtkursk-dyuym.ru{route}', html)
                    self.assertIn('<nav class="site-nav"', html)

    def test_published_legacy_paths_and_assets_remain_available(self):
        paths = ["/", "/index.html", "/projects/kryak.html", "/projects/mediazavry.html",
                 "/journals/media-camp.html", "/styles.css", "/script.js",
                 "/assets/images/favicon.png", "/assets/journal-covers/media-camp-01.webp"]
        for path in paths:
            with self.subTest(path=path):
                request = Request(self.base + path, method="HEAD")
                with urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200)

    def test_all_local_page_links_and_assets_exist_in_the_artifact(self):
        pages = {}
        for route in ROUTES:
            parsed = PageParser()
            parsed.feed(self.built_target(route).read_text(encoding="utf-8"))
            pages[route] = parsed

        for route, page in pages.items():
            with self.subTest(route=route):
                base = self.base + route
                references = [link.get("href", "") for link in page.all_links] + page.local_references
                for reference in references:
                    resolved = urlsplit(urljoin(base, reference))
                    if resolved.netloc != urlsplit(self.base).netloc:
                        continue
                    target_path = unquote(resolved.path)
                    target = self.built_target(target_path)
                    self.assertTrue(target.is_file(), f"{route}: missing {reference} -> {target}")
                    if resolved.fragment and target_path in pages:
                        self.assertIn(unquote(resolved.fragment), pages[target_path].ids, reference)


if __name__ == "__main__":
    unittest.main()
