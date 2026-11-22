from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

from tools.site_routes import ROUTES


ROOT = Path(__file__).resolve().parents[1]
ROUTE_BY_SOURCE = {ROOT / source: route for route, source in ROUTES.items()}


def resolve_local(page_path, url_path):
    """Resolve a public path to its source file for local checks."""
    if not url_path:
        return page_path
    decoded = unquote(url_path)
    if decoded in ROUTES:
        return ROOT / ROUTES[decoded]
    if decoded.startswith("/"):
        return ROOT / decoded.lstrip("/")
    return (page_path.parent / decoded).resolve()


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.navigation_links = []
        self.navigation_anchors = []
        self.navigation_buttons = []
        self.navigation_lists = []
        self.navigation_dropdowns = []
        self.navigation_submenus = []
        self.navigation_menu_labels = []
        self.details_stack = []
        self.local_references = []
        self.all_links = []
        self.anchors = []
        self.current_page_anchor = None
        self.icons = []
        self.images = []
        self.iframes = []
        self.journal_cards = []
        self.class_counts = Counter()
        self.headings = []
        self.current_heading = None
        self.canonical_url = None
        self.paragraphs = {"footer-credit": [], "footer-notice": []}
        self.in_navigation = False
        self.in_footer = False
        self.footer_text = []
        self.footer_credit_links = []
        self.current_paragraph = None
        self.current_anchor = None
        self.current_summary = None
        self.current_menu_label = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        self.class_counts.update(classes)
        if "journal-card" in classes:
            self.journal_cards.append(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.all_links.append(attrs)
            self.current_page_anchor = {"attrs": attrs, "text": []}
            self.anchors.append(self.current_page_anchor)
            if self.in_footer and self.current_paragraph == "footer-credit":
                self.footer_credit_links.append(attrs)
        if tag == "img":
            self.images.append(attrs)
        if tag == "iframe":
            self.iframes.append(attrs)
        if tag in {"h1", "h2", "h3"}:
            self.current_heading = {"tag": tag, "text": []}
            self.headings.append(self.current_heading)
        if tag == "nav" and "site-nav" in classes:
            self.in_navigation = True
        if self.in_navigation and tag == "button":
            self.navigation_buttons.append(attrs)
        if self.in_navigation and tag == "ul" and "nav-list" in classes:
            self.navigation_lists.append(attrs)
        if self.in_navigation and tag == "a":
            self.navigation_links.append(attrs.get("href", ""))
            self.current_anchor = {
                "attrs": attrs,
                "text": [],
                "owner": self.details_stack[-1] if self.details_stack else None,
            }
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
        if tag == "image" and "href" in attrs:
            self.local_references.append(attrs["href"])
        if tag == "link" and "href" in attrs:
            self.local_references.append(attrs["href"])
            rel = attrs.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonical_url = attrs["href"]
            if "icon" in rel:
                self.icons.append(attrs)

    def handle_endtag(self, tag):
        if self.current_heading is not None and tag == self.current_heading["tag"]:
            self.current_heading["text"] = " ".join("".join(self.current_heading["text"]).split())
            self.current_heading = None
        if tag == "a" and self.current_anchor is not None:
            self.current_anchor["text"] = " ".join("".join(self.current_anchor["text"]).split())
            self.current_anchor = None
        if tag == "a" and self.current_page_anchor is not None:
            self.current_page_anchor["text"] = " ".join("".join(self.current_page_anchor["text"]).split())
            self.current_page_anchor = None
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
        if self.current_heading is not None:
            self.current_heading["text"].append(data)
        if self.current_anchor is not None:
            self.current_anchor["text"].append(data)
        if self.current_page_anchor is not None:
            self.current_page_anchor["text"].append(data)
        if self.current_summary is not None:
            self.current_summary["text"].append(data)
        if self.current_menu_label is not None:
            self.current_menu_label["text"].append(data)
        if self.in_footer:
            self.footer_text.append(data)
        if self.current_paragraph:
            self.paragraphs[self.current_paragraph].append(data)


class HomePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PageParser()
        cls.page.feed((ROOT / "index.html").read_text(encoding="utf-8"))

    def test_navigation_links_point_to_existing_targets(self):
        self.assertIn("/главная", self.page.navigation_links)
        counts = Counter(self.page.ids)
        self.assertTrue(all(count == 1 for count in counts.values()), "Page IDs must be unique")
        for link in self.page.navigation_links:
            self.assertTrue(link, "Navigation links must have a destination")
            url = urlsplit(link)
            if link.startswith("#"):
                self.assertEqual(counts[link[1:]], 1, f"Missing target for {link}")
            elif not url.scheme and not url.netloc:
                self.assertTrue(resolve_local(ROOT / "index.html", url.path).is_file(), f"Missing page for {link}")

    def test_navigation_has_home_link_and_two_native_dropdown_sections(self):
        homes = [
            anchor for anchor in self.page.navigation_anchors
            if anchor["attrs"].get("href") == "/главная" and anchor["text"] == "Главная"
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

    def test_site_creation_credit_links_to_kryak_website(self):
        links = [
            anchor for anchor in self.page.anchors
            if anchor["text"] == "МХ «КРЯК»"
            and "kryak-link" in anchor["attrs"].get("class", "").split()
        ]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["attrs"].get("href"), "https://www.yacluster-kryak.ru/")
        self.assertEqual(links[0]["attrs"].get("target"), "_blank")
        self.assertTrue({"noopener", "noreferrer"} <= set(links[0]["attrs"].get("rel", "").split()))
        self.assertFalse(any(
            link.get("href") == "https://sites.google.com/view/masterkart"
            for link in self.page.all_links
        ))

    def test_pages_domain_and_canonical_url_match(self):
        domain = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
        self.assertEqual(domain, "www.cdtkursk-dyuym.ru")
        self.assertEqual(self.page.canonical_url, f"https://{domain}/главная")
        self.assertTrue((ROOT / ".nojekyll").is_file())

    def test_address_and_embedded_map_remain_without_open_map_link(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("г. Курск, проспект Дружбы, 2", html)
        self.assertIn("address", self.page.ids)
        self.assertEqual(self.page.class_counts["map-container"], 1)
        self.assertEqual(self.page.class_counts["map-fallback"], 1)
        self.assertTrue(any(
            ref.startswith("https://api-maps.yandex.ru/services/constructor/")
            for ref in self.page.local_references
        ))
        self.assertNotIn("Открыть на карте", html)
        self.assertEqual(self.page.class_counts["map-link"], 0)
        self.assertFalse(any(
            urlsplit(link.get("href", "")).netloc == "yandex.ru"
            and urlsplit(link.get("href", "")).path == "/maps/"
            for link in self.page.all_links
        ))

    def test_local_page_and_stylesheet_assets_exist(self):
        for reference in self.page.local_references:
            url = urlsplit(reference)
            if not url.scheme and not url.netloc:
                self.assertTrue(resolve_local(ROOT / "index.html", url.path).is_file(), reference)

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


class AllPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = (
            ROOT / "index.html",
            ROOT / "projects/kryak.html",
            ROOT / "projects/mediazavry.html",
            ROOT / "journals/svetlyachok.html",
            ROOT / "journals/volga-yunpress.html",
            ROOT / "journals/media-camp.html",
            ROOT / "journals/48-volna.html",
            ROOT / "journals/globus.html",
        )
        cls.pages = {}
        for path in cls.paths:
            page = PageParser()
            page.feed(path.read_text(encoding="utf-8"))
            cls.pages[path] = page

    def test_no_decorative_background_circles(self):
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                self.assertEqual(page.class_counts["animated-bg"], 0)
                self.assertEqual(page.class_counts["floating-shapes"], 0)
                self.assertEqual(page.class_counts["shape"], 0)

        for stylesheet in (
            ROOT / "styles.css",
            ROOT / "journals/journals.css",
            ROOT / "projects/kryak.css",
            ROOT / "projects/mediazavry.css",
        ):
            with self.subTest(stylesheet=stylesheet.relative_to(ROOT)):
                content = stylesheet.read_text(encoding="utf-8")
                self.assertNotIn(".animated-bg", content)
                self.assertNotIn(".floating-shapes", content)
                self.assertNotRegex(content, r"(?m)^\.shape\s*\{")
                self.assertNotIn("@keyframes float", content)

    def test_all_pages_use_the_school_logo_as_favicon(self):
        favicon = ROOT / "assets/images/favicon.png"
        image = favicon.read_bytes()
        self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(int.from_bytes(image[16:20], "big"), 96)
        self.assertEqual(int.from_bytes(image[20:24], "big"), 96)
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                self.assertEqual(len(page.icons), 1)
                self.assertEqual(page.icons[0].get("href"), "/assets/images/favicon.png")
                self.assertEqual(page.icons[0].get("type"), "image/png")
                self.assertEqual(page.icons[0].get("sizes"), "96x96")
                self.assertEqual(resolve_local(path, page.icons[0]["href"]), favicon)

    def test_brand_and_mobile_toggle_are_consistent(self):
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                brands = [
                    anchor for anchor in page.navigation_anchors
                    if "nav-brand" in anchor["attrs"].get("class", "").split()
                ]
                self.assertEqual(len(brands), 1)
                self.assertEqual(brands[0]["text"], "ДЮйМ")
                self.assertEqual(brands[0]["attrs"]["href"], "/главная")
                self.assertEqual(resolve_local(path, brands[0]["attrs"]["href"]), ROOT / "index.html")
                self.assertEqual(
                    brands[0]["attrs"].get("aria-label"), "Медиашкола «ДЮйМ» — на главную"
                )

                toggles = [
                    button for button in page.navigation_buttons
                    if "nav-toggle" in button.get("class", "").split()
                ]
                self.assertEqual(len(toggles), 1)
                self.assertEqual(toggles[0].get("type"), "button")
                self.assertEqual(toggles[0].get("aria-expanded"), "false")
                self.assertEqual(toggles[0].get("aria-label"), "Открыть меню")
                self.assertEqual(toggles[0].get("aria-controls"), "site-nav-menu")
                self.assertEqual(len(page.navigation_lists), 1)
                self.assertEqual(page.navigation_lists[0].get("id"), toggles[0]["aria-controls"])
                self.assertEqual(page.ids.count("site-nav-menu"), 1)

    def test_project_menu_has_exactly_two_working_links_on_every_page(self):
        expected = [
            ("МХ «КРЯК»", ROOT / "projects/kryak.html"),
            ("«МЕДИАЗАВРЫ, вперёд!»", ROOT / "projects/mediazavry.html"),
        ]
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                self.assertEqual(
                    [item["summary"] for item in page.navigation_dropdowns],
                    ["Наши журналы", "Проекты"],
                )
                for dropdown in page.navigation_dropdowns:
                    self.assertEqual(dropdown["attrs"].get("name"), "primary-navigation")
                    self.assertNotIn("open", dropdown["attrs"])
                    self.assertEqual(dropdown["panels"], 1)
                projects = page.navigation_dropdowns[1]
                self.assertFalse(any(item["parent"] is projects for item in page.navigation_submenus))
                self.assertEqual(
                    [item["text"] for item in page.navigation_menu_labels if item["owner"] is projects],
                    [title for title, _ in expected],
                )
                anchors = [item for item in page.navigation_anchors if item["owner"] is projects]
                self.assertEqual(
                    [(a["text"], resolve_local(path, urlsplit(a["attrs"]["href"]).path))
                     for a in anchors],
                    expected,
                )
                for anchor, (_, target) in zip(anchors, expected):
                    self.assertTrue(target.is_file())
                    self.assertEqual(anchor["attrs"]["href"], ROUTE_BY_SOURCE[target])
                    self.assertEqual(anchor["attrs"].get("aria-current") == "page", path == target)

                home = next(a for a in page.navigation_anchors if a["text"] == "Главная")
                home_url = urlsplit(home["attrs"]["href"])
                self.assertEqual(home_url.path, "/главная")
                self.assertEqual(resolve_local(path, home_url.path), ROOT / "index.html")
                self.assertEqual(home_url.fragment, "")
                self.assertEqual(home["attrs"].get("aria-current") == "page", path == ROOT / "index.html")

    def test_kryak_formal_name_is_updated(self):
        old_names = (
            "молодёжный холдинг",
            "молодёжного холдинга",
            "картографический региональный я-кластер",
            "президент холдинга",
        )
        for path in self.paths:
            with self.subTest(page=path.relative_to(ROOT)):
                html = path.read_text(encoding="utf-8").casefold()
                for name in old_names:
                    self.assertNotIn(name, html)

        kryak = (ROOT / "projects/kryak.html").read_text(encoding="utf-8")
        mediazavry = (ROOT / "projects/mediazavry.html").read_text(encoding="utf-8")
        self.assertIn("<title>Молодёжное движение «КРЯК»</title>", kryak)
        self.assertIn("отделение молодёжного движения «КРЯК»", kryak)
        self.assertIn("Президент движения", kryak)
        self.assertIn("Молодёжное движение «КРЯК»", mediazavry)

    def test_journal_menu_is_consistent_across_pages(self):
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                journals = page.navigation_dropdowns[0]
                submenus = [item for item in page.navigation_submenus if item["parent"] is journals]
                self.assertEqual(len(submenus), 1)
                self.assertEqual(submenus[0]["summary"], "Медиасобытия")
                labels = [
                    item["text"] for item in page.navigation_menu_labels
                    if item["owner"] is journals or item["owner"] is submenus[0]
                ]
                self.assertEqual(
                    labels,
                    ["Светлячок", "Медиасобытия", "Волга-ЮНПРЕСС", "Media Camp", "48-ая волна", "Глобус"],
                )

    def test_journal_links_work_on_every_page(self):
        expected = [
            ("Светлячок", ROOT / "journals/svetlyachok.html"),
            ("Волга-ЮНПРЕСС", ROOT / "journals/volga-yunpress.html"),
            ("Media Camp", ROOT / "journals/media-camp.html"),
            ("48-ая волна", ROOT / "journals/48-volna.html"),
            ("Глобус", ROOT / "journals/globus.html"),
        ]
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                names = {name for name, _ in expected}
                anchors = [a for a in page.navigation_anchors if a["text"] in names]
                self.assertEqual([a["text"] for a in anchors], [name for name, _ in expected])
                for anchor, (name, target) in zip(anchors, expected):
                    href = urlsplit(anchor["attrs"]["href"])
                    self.assertEqual(resolve_local(path, href.path), target, name)
                    self.assertEqual(href.path, ROUTE_BY_SOURCE[target])
                    self.assertTrue(target.is_file())
                    self.assertEqual(anchor["attrs"].get("aria-current") == "page", path == target)
                    self.assertEqual(
                        anchor["owner"]["summary"],
                        "Медиасобытия" if name == "Волга-ЮНПРЕСС" else "Наши журналы",
                    )
                self.assertFalse(any(a["text"] == "Медиасобытия" for a in page.navigation_anchors))

    def test_journal_archives_and_issue_links_are_present_without_javascript(self):
        archives = [
            ("svetlyachok.html", "Журнал «Светлячок»", 61, "cloud.mail.ru"),
            ("volga-yunpress.html", "Газета «Дневник фестиваля»", 1, "www.calameo.com"),
            ("media-camp.html", "Media Camp", 1, "www.calameo.com"),
            ("48-volna.html", "«Сорок восьмая волна»", 4, "www.calameo.com"),
            ("globus.html", "«Глобус»", 4, "www.calameo.com"),
        ]
        for filename, heading, count, host in archives:
            with self.subTest(page=filename):
                page = self.pages[ROOT / "journals" / filename]
                self.assertEqual([h["text"] for h in page.headings if h["tag"] == "h1"], [heading])
                self.assertEqual(len(page.journal_cards), count)
                self.assertTrue(all("hidden" not in card for card in page.journal_cards))
                issue_links = [a for a in page.all_links if urlsplit(a.get("href", "")).netloc == host]
                self.assertEqual(len(issue_links), count)
        svet = self.pages[ROOT / "journals/svetlyachok.html"]
        self.assertEqual([int(card["data-issue-number"]) for card in svet.journal_cards], list(range(1, 62)))
        self.assertEqual(svet.journal_cards[55]["data-period"], "зима 2024–2025 (декабрь 2024 / январь-февраль 2025)")
        self.assertIn("/journals/svetlyachok.js", svet.local_references)

        media_camp = self.pages[ROOT / "journals/media-camp.html"]
        self.assertTrue(any(
            link.get("href") == "https://www.calameo.com/read/006994183460c918117ed"
            for link in media_camp.all_links
        ))
        self.assertTrue(any(
            image.get("src") == "/assets/journal-covers/media-camp-01.webp"
            and image.get("alt") == "Обложка Media Camp, выпуск 1/2023"
            for image in media_camp.images
        ))
        self.assertIn("Выпуск 1/2023", (ROOT / "journals/media-camp.html").read_text(encoding="utf-8"))

    def test_all_footers_and_canonical_urls(self):
        credit = "© МБУ ДО «Центр детского творчества», 2025 – 2026 | Размещено при поддержке МХ «КРЯК»"
        notice = "Использование материалов, размещённых на этом сайте, возможно только при обязательном указании автора и ссылки на источник."
        domain = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                text = {key: " ".join("".join(parts).split()) for key, parts in page.paragraphs.items()}
                self.assertEqual(text["footer-credit"], credit)
                self.assertEqual(text["footer-notice"], notice)
                self.assertEqual(page.footer_credit_links, [])
                self.assertEqual(page.canonical_url, f"https://{domain}{ROUTE_BY_SOURCE[path]}")

    def test_footer_has_no_back_to_top_link(self):
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                self.assertNotIn("наверх", " ".join(page.footer_text).casefold())

    def test_links_assets_and_fragments_are_valid(self):
        stylesheets = set()
        for path, page in self.pages.items():
            with self.subTest(page=path.relative_to(ROOT)):
                counts = Counter(page.ids)
                self.assertTrue(all(count == 1 for count in counts.values()), "Page IDs must be unique")
                for link in page.all_links:
                    href = link.get("href", "")
                    self.assertTrue(href, f"Empty link on {path}")
                    if link.get("target") == "_blank":
                        self.assertTrue({"noopener", "noreferrer"} <= set(link.get("rel", "").split()))
                    url = urlsplit(href)
                    if url.scheme or url.netloc:
                        continue
                    target = resolve_local(path, url.path)
                    self.assertTrue(target.is_file(), f"{path}: missing {href}")
                    if url.fragment and target in self.pages:
                        self.assertEqual(Counter(self.pages[target].ids)[unquote(url.fragment)], 1, href)
                for image in page.images:
                    self.assertIn("alt", image, f"Image without alt: {image}")
                    source = urlsplit(image.get("src", ""))
                    self.assertFalse(source.scheme or source.netloc, f"Image is not local: {source.geturl()}")
                    self.assertTrue(source.path, "Image source is empty")
                for ref in page.local_references:
                    url = urlsplit(ref)
                    if not url.scheme and not url.netloc:
                        target = resolve_local(path, url.path)
                        self.assertTrue(target.is_file(), f"{path}: missing {ref}")
                        if target.suffix == ".css":
                            stylesheets.add(target)

        for stylesheet in stylesheets:
            content = stylesheet.read_text(encoding="utf-8")
            for ref in re.findall(r"url\(\s*['\"]?([^\s)'\"]+)", content):
                url = urlsplit(ref)
                if not url.scheme and not url.netloc:
                    self.assertTrue(
                        (stylesheet.parent / unquote(url.path)).is_file(),
                        f"{stylesheet}: missing {ref}",
                    )

    def test_kryak_map_legend_and_info_block_are_spaced(self):
        kryak = self.pages[ROOT / "projects/kryak.html"]
        self.assertIn("mapViews", kryak.ids)
        self.assertEqual(kryak.class_counts["legend-section"], 3)
        self.assertEqual(kryak.class_counts["info-section"], 1)
        css = (ROOT / "projects/kryak.css").read_text(encoding="utf-8")
        rule = re.search(r"#mapViews:not\(\[hidden\]\)\s*\+\s*\.info-section\s*\{([^}]*)\}", css)
        self.assertIsNotNone(rule, "The visible map should be separated from the information block")
        gap = re.search(r"\bmargin-top\s*:\s*([0-9]+(?:\.[0-9]+)?)px\s*;", rule.group(1))
        self.assertIsNotNone(gap)
        self.assertGreater(float(gap.group(1)), 0)

    def test_project_content_and_map_controls_are_present(self):
        kryak = self.pages[ROOT / "projects/kryak.html"]
        media = self.pages[ROOT / "projects/mediazavry.html"]
        self.assertEqual([h["text"] for h in kryak.headings if h["tag"] == "h1"], ["МХ «КРЯК»"])
        self.assertEqual([h["text"] for h in media.headings if h["tag"] == "h1"], ["«МЕДИАЗАВРЫ, вперёд!»"])
        for page, names in (
            (kryak, ["Роман Бугаенко", "Светлана Белоусова", "Полина Пожидаева", "Наталья Шеховцова", "Артём Русанов", "Кирилл Киреев"]),
            (media, ["Мария Федосова", "Светлана Белоусова"]),
        ):
            self.assertIn("/projects/project-common.css", page.local_references)
            self.assertEqual(page.class_counts["team-member"], len(names))
            self.assertEqual(
                [image["alt"] for image in page.images if "member-photo" in image.get("class", "").split()],
                names,
            )
        self.assertEqual(kryak.class_counts["supporter-item"], 21)
        self.assertTrue({
            "mapFallback", "mapViews", "worldSvg", "mapSvg", "countrySvg",
            "openWorldMap", "openRussiaMap", "openBelarusMap", "russiaData", "countryData",
        } <= set(kryak.ids))
        self.assertNotIn("worldData", kryak.ids)
        self.assertNotIn("Список стран и статусов", (ROOT / "projects/kryak.html").read_text(encoding="utf-8"))
        self.assertNotIn("worldData", (ROOT / "projects/kryak.js").read_text(encoding="utf-8"))
        self.assertEqual(media.class_counts["comic-series"], 5)
        self.assertEqual(media.class_counts["comic-page"], 35)
        self.assertEqual(len(media.iframes), 1)
        self.assertEqual(media.iframes[0].get("title"), "Медиазавры на каникулах")
        self.assertEqual(
            media.iframes[0].get("src"),
            "https://vk.com/video_ext.php?oid=-224639177&id=456239043",
        )
        self.assertTrue(any(link.get("href") == media.iframes[0]["src"] for link in media.all_links))


if __name__ == "__main__":
    unittest.main()
