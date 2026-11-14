from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.navigation_links = []
        self.local_references = []
        self.canonical_url = None
        self.paragraphs = {"footer-credit": [], "footer-notice": []}
        self.menu_button = None
        self.in_navigation = False
        self.in_footer = False
        self.current_paragraph = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "nav" and "site-nav" in classes:
            self.in_navigation = True
        if self.in_navigation and tag == "a":
            self.navigation_links.append(attrs.get("href", ""))
        if tag == "button" and "nav-toggle" in classes:
            self.menu_button = attrs
        if tag == "footer":
            self.in_footer = True
        if self.in_footer and tag == "p":
            self.current_paragraph = next(
                (name for name in self.paragraphs if name in classes), None
            )
        if tag in {"img", "script"} and "src" in attrs:
            self.local_references.append(attrs["src"])
        if tag == "link" and "href" in attrs:
            self.local_references.append(attrs["href"])
            if "canonical" in attrs.get("rel", "").split():
                self.canonical_url = attrs["href"]

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_navigation = False
        if tag == "p":
            self.current_paragraph = None
        if tag == "footer":
            self.in_footer = False

    def handle_data(self, data):
        if self.current_paragraph:
            self.paragraphs[self.current_paragraph].append(data)


class HomePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PageParser()
        cls.page.feed((ROOT / "index.html").read_text(encoding="utf-8"))

    def test_navigation_points_to_existing_unique_sections(self):
        self.assertEqual(
            set(self.page.navigation_links),
            {"#home", "#mission", "#directions", "#teacher", "#details", "#address", "#contacts"},
        )
        counts = Counter(self.page.ids)
        self.assertTrue(all(count == 1 for count in counts.values()), "Page IDs must be unique")
        for link in self.page.navigation_links:
            self.assertEqual(counts[link[1:]], 1, f"Missing target for {link}")

    def test_menu_has_accessible_initial_state(self):
        button = self.page.menu_button
        self.assertIsNotNone(button)
        self.assertEqual(button.get("type"), "button")
        self.assertEqual(button.get("aria-controls"), "site-navigation")
        self.assertEqual(button.get("aria-expanded"), "false")
        self.assertIn("hidden", button)  # The links remain visible without JavaScript.
        self.assertIn("site-navigation", self.page.ids)

    def test_footer_contains_the_requested_text(self):
        text = {
            key: " ".join("".join(parts).split())
            for key, parts in self.page.paragraphs.items()
        }
        self.assertEqual(
            text["footer-credit"],
            "© МБУ ДО «Центр детского творчества», 2025 – 2026 | Размещено при поддержке МХ «КРЯК»",
        )
        self.assertEqual(
            text["footer-notice"],
            "Использование материалов, размещённых на этом сайте, возможно только при обязательном указании автора и ссылки на источник.",
        )

    def test_pages_domain_and_canonical_url_match(self):
        domain = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
        self.assertEqual(domain, "www.cdtkursk-dyuym.ru")
        self.assertEqual(self.page.canonical_url, f"https://{domain}/")
        self.assertTrue((ROOT / ".nojekyll").is_file())

    def test_local_page_and_stylesheet_assets_exist(self):
        for reference in self.page.local_references:
            url = urlsplit(reference)
            if not url.scheme and not url.netloc:
                self.assertTrue((ROOT / unquote(url.path)).is_file(), reference)

        for stylesheet in (
            ROOT / "styles.css",
            ROOT / "assets/vendor/fontawesome/css/solid.min.css",
        ):
            content = stylesheet.read_text(encoding="utf-8")
            for reference in re.findall(r"url\(\s*['\"]?([^\s)'\"]+)", content):
                url = urlsplit(reference)
                if not url.scheme and not url.netloc:
                    self.assertTrue(
                        (stylesheet.parent / unquote(url.path)).is_file(),
                        f"{stylesheet.name}: {reference}",
                    )


if __name__ == "__main__":
    unittest.main()
