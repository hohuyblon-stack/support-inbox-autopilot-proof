from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        for name in ("href", "src"):
            value = values.get(name)
            if value:
                self.references.append(value)


class PublicPageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_page_links_to_executable_evaluation_result(self):
        self.assertIn('href="evaluation/results.json"', self.html)

    def test_page_has_explicit_non_affiliation_boundary(self):
        self.assertIn(
            "not affiliated with or endorsed by Gorgias or Shopify", self.html
        )

    def test_all_relative_page_assets_exist(self):
        parser = LinkCollector()
        parser.feed(self.html)
        missing = []
        for reference in parser.references:
            if reference.startswith(("#", "mailto:", "http://", "https://")):
                continue
            path = reference.split("#", 1)[0].split("?", 1)[0]
            if path and not (ROOT / path).exists():
                missing.append(reference)
        self.assertEqual(missing, [])

    def test_page_keeps_fifteen_curated_ticket_rows(self):
        rows = re.findall(r'<tr id="ticket-[^"]+"[^>]+data-route=', self.html)
        self.assertEqual(len(rows), 15)

    def test_page_avoids_unsupported_maturity_adjectives(self):
        lowered = self.html.lower()
        for phrase in ("enterprise-grade", "production-ready", "state-of-the-art"):
            self.assertNotIn(phrase, lowered)


if __name__ == "__main__":
    unittest.main()
