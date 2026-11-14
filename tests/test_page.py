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
        self.navigation_anchors = []
        self.navigation_dropdowns = []
        self.navigation_submenus = []
        self.navigation_menu_labels = []
        self.details_stack = []
        self.local_references = []
        self.canonical_url = None
        self.paragraphs = {"footer-credit": [], "footer-notice": []}
        self.in_navigation = False
        self.in_footer = False
        self.current_paragraph = None
        self.current_anchor = None
        self.current_summary = None
        self.current_menu_label = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "nav" and "site-nav" in classes:
            self.in_navigation = True
        if self.in_navigation and tag == "a":
            self.navigation_links.append(attrs.get("href", ""))
            self.current_anchor = {"attrs": attrs, "text": []}
            self.navigation_anchors.append(self.current_anchor)
        if self.in_navigation and tag == "details":
            dropdown = {
                "attrs": attrs,
                "summary": None,
                "panels": 0,
                "parent": self.details_stack[-1] if self.details_stack else None,
            }
            self.details_stack.append(dropdown)
            if "nav-dropdown" in classes:
                self.navigation_dropdowns.append(dropdown)
            if "nav-submenu" in classes:
                self.navigation_submenus.append(dropdown)
        if self.in_navigation and self.details_stack and "nav-dropdown-panel" in classes:
            self.details_stack[-1]["panels"] += 1
        if self.in_navigation and tag == "summary":
            self.current_summary = {
                "owner": self.details_stack[-1] if self.details_stack else None,
                "text": [],
            }
        if self.in_navigation and tag == "span" and "nav-menu-label" in classes:
            self.current_menu_label = {
                "owner": self.details_stack[-1] if self.details_stack else None,
                "text": [],
            }
            self.navigation_menu_labels.append(self.current_menu_label)
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
        if tag == "a" and self.current_anchor is not None:
            self.current_anchor["text"] = " ".join("".join(self.current_anchor["text"]).split())
            self.current_anchor = None
        if tag == "span" and self.current_menu_label is not None:
            self.current_menu_label["text"] = " ".join("".join(self.current_menu_label["text"]).split())
            self.current_menu_label = None
        if tag == "summary" and self.current_summary is not None:
            owner = self.current_summary["owner"]
            if owner is not None:
                owner["summary"] = " ".join("".join(self.current_summary["text"]).split())
            self.current_summary = None
        if self.in_navigation and tag == "details" and self.details_stack:
            self.details_stack.pop()
        if tag == "nav":
            self.in_navigation = False
        if tag == "p":
            self.current_paragraph = None
        if tag == "footer":
            self.in_footer = False

    def handle_data(self, data):
        if self.current_anchor is not None:
            self.current_anchor["text"].append(data)
        if self.current_summary is not None:
            self.current_summary["text"].append(data)
        if self.current_menu_label is not None:
            self.current_menu_label["text"].append(data)
        if self.current_paragraph:
            self.paragraphs[self.current_paragraph].append(data)


class HomePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PageParser()
        cls.page.feed((ROOT / "index.html").read_text(encoding="utf-8"))

    def test_navigation_links_point_to_existing_targets(self):
        self.assertIn("#home", self.page.navigation_links)
        counts = Counter(self.page.ids)
        self.assertTrue(all(count == 1 for count in counts.values()), "Page IDs must be unique")
        for link in self.page.navigation_links:
            self.assertTrue(link, "Navigation links must have a destination")
            url = urlsplit(link)
            if link.startswith("#"):
                self.assertEqual(counts[link[1:]], 1, f"Missing target for {link}")
            elif not url.scheme and not url.netloc:
                self.assertTrue((ROOT / unquote(url.path)).is_file(), f"Missing page for {link}")

    def test_navigation_has_home_link_and_two_native_dropdown_sections(self):
        homes = [
            anchor for anchor in self.page.navigation_anchors
            if anchor["attrs"].get("href") == "#home"
        ]
        self.assertEqual(len(homes), 1)
        self.assertEqual(homes[0]["text"], "Главная")
        self.assertEqual(homes[0]["attrs"].get("aria-current"), "page")

        self.assertEqual(
            [dropdown["summary"] for dropdown in self.page.navigation_dropdowns],
            ["Наши журналы", "Проекты"],
        )
        for dropdown in self.page.navigation_dropdowns:
            self.assertEqual(dropdown["attrs"].get("name"), "primary-navigation")
            self.assertNotIn("open", dropdown["attrs"])
            self.assertEqual(dropdown["panels"], 1)

    def test_journal_menu_has_requested_entries_and_nested_section(self):
        journals = self.page.navigation_dropdowns[0]
        submenus = [item for item in self.page.navigation_submenus if item["parent"] is journals]
        self.assertEqual(len(submenus), 1)
        submenu = submenus[0]
        self.assertEqual(submenu["summary"], "Медиасобытия")
        self.assertNotIn("open", submenu["attrs"])

        labels = [
            item for item in self.page.navigation_menu_labels
            if item["owner"] is journals or item["owner"] is submenu
        ]
        self.assertEqual(
            [item["text"] for item in labels],
            ["Светлячок", "Медиасобытия", "Волга-ЮНПРЕСС", "Media Camp", "48-ая волна", "Глобус"],
        )
        for item in labels:
            expected_owner = (
                submenu if item["text"] in {"Медиасобытия", "Волга-ЮНПРЕСС"} else journals
            )
            self.assertIs(item["owner"], expected_owner, item["text"])

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
