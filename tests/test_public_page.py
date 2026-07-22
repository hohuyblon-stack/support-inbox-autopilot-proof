from html.parser import HTMLParser
import json
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
        cls.market = json.loads(
            (ROOT / "evaluation" / "market_quality_results.json").read_text()
        )

    def test_page_links_to_executable_evaluation_result(self):
        self.assertIn('href="evaluation/results.json"', self.html)

    def test_page_has_explicit_non_affiliation_boundary(self):
        self.assertIn(
            "not affiliated with or endorsed by Gorgias or Shopify", self.html
        )

    def test_page_exposes_the_current_blocking_market_verdict(self):
        self.assertEqual(self.market["verdict"], "NOT_MARKET_READY")
        self.assertIn(self.market["verdict"], self.html)
        self.assertIn(f'{self.market["score"]:g}/100', self.html)
        self.assertIn(f'threshold {self.market["threshold"]:g}', self.html)
        self.assertIn(
            f'{len(self.market["critical_failures"])} critical gaps', self.html
        )
        self.assertIn('href="docs/MARKET_QUALITY_GATE.md"', self.html)

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
