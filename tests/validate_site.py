from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.scripts = []
        self.images = []
        self.headings = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        if tag == "script" and "src" in attributes:
            self.scripts.append(attributes["src"])
        if tag == "img" and "src" in attributes:
            self.images.append((attributes["src"], attributes.get("alt", "")))
        if tag in {"h1", "h2", "h3"}:
            self.headings.append(tag)


class SiteValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)
        cls.javascript = (ROOT / "script.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "styles.css").read_text(encoding="utf-8")

    def test_required_sections_and_semantic_structure(self):
        self.assertIn("<header>", self.html)
        self.assertIn("<main>", self.html)
        self.assertIn("<footer", self.html)
        self.assertIn("<h1>", self.html)
        self.assertIn("sobre-mi", self.parser.ids)
        self.assertIn("habilidades", self.parser.ids)
        self.assertIn("contacto", self.parser.ids)
        self.assertIn("toggleHabilidades", self.parser.ids)
        self.assertIn("listaHabilidades", self.parser.ids)

    def test_navigation_targets_exist(self):
        targets = {link[1:] for link in self.parser.links if link.startswith("#")}
        self.assertTrue(targets.issubset(self.parser.ids))

    def test_local_assets_exist_and_images_are_described(self):
        for source, alt in self.parser.images:
            self.assertTrue((ROOT / source).is_file(), source)
            self.assertTrue(alt.strip(), source)
        for source in self.parser.scripts:
            self.assertTrue((ROOT / source).is_file(), source)

    def test_interaction_hooks_are_present(self):
        self.assertIn('getElementById("toggleHabilidades")', self.javascript)
        self.assertIn('getElementById("listaHabilidades")', self.javascript)
        self.assertIn('classList.toggle("oculto")', self.javascript)
        self.assertRegex(self.styles, r"\.oculto\s*\{\s*display:\s*none\s*;")


if __name__ == "__main__":
    unittest.main(verbosity=2)
