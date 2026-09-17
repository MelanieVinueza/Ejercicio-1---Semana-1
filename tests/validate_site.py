"""Validación estática del sitio: HTML semántico, HTML5, ARIA y enlaces seguros.

Ejecutar localmente con:
    python -m unittest discover -s tests -p "validate_site.py" -v
"""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import unittest


ROOT = Path(__file__).resolve().parents[1]

# Dominios legítimos de YouTube (incluye el dominio de incrustación
# respetuoso con la privacidad youtube-nocookie.com).
YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtube-nocookie.com",
}

SCHEMES_PELIGROSOS = ("javascript:", "data:", "vbscript:")


class SiteParser(HTMLParser):
    """Recolecta información estructural del HTML para los tests."""

    def __init__(self):
        super().__init__()
        self.doctype = None
        self.html_lang = None
        self.ids = set()
        self.links = []
        self.buttons = []
        self.scripts = []
        self.images = []
        self.headings = []
        self.uses_table = False
        self.aria_references = {}
        self._link_stack = []
        self._button_stack = []

    def handle_decl(self, decl):
        if decl.strip().upper().startswith("DOCTYPE"):
            self.doctype = decl

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "html":
            self.html_lang = attributes.get("lang")
        if "id" in attributes:
            self.ids.add(attributes["id"])

        if tag == "a":
            if "href" in attributes:
                link = {
                    "href": attributes["href"],
                    "target": attributes.get("target", ""),
                    "rel": attributes.get("rel", ""),
                    "aria-label": attributes.get("aria-label", ""),
                    "title": attributes.get("title", ""),
                    "text": "",
                }
                self.links.append(link)
                self._link_stack.append(link)
        if tag == "button":
            button = {"attrs": attributes, "text": ""}
            self.buttons.append(button)
            self._button_stack.append(button)
        if tag == "script" and "src" in attributes:
            self.scripts.append(attributes["src"])
        if tag == "img" and "src" in attributes:
            self.images.append((attributes["src"], attributes.get("alt", "")))
        if tag in {"h1", "h2", "h3", "h4"}:
            self.headings.append(tag)
        if tag == "table":
            self.uses_table = True

        # Referencias ARIA que deben apuntar a ids existentes en el documento.
        for attr in ("aria-controls", "aria-labelledby", "aria-describedby",
                     "aria-owns", "aria-activedescendant", "aria-details"):
            value = attributes.get(attr)
            if value:
                self.aria_references.setdefault(attr, []).extend(value.split())

    def handle_data(self, data):
        if self._link_stack:
            self._link_stack[-1]["text"] += data
        if self._button_stack:
            self._button_stack[-1]["text"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self._link_stack:
            link = self._link_stack.pop()
            link["text"] = " ".join(link["text"].split())
        if tag == "button" and self._button_stack:
            button = self._button_stack.pop()
            button["text"] = " ".join(button["text"].split())


class SiteValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)
        cls.javascript = (ROOT / "script.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "styles.css").read_text(encoding="utf-8")

    # ---------- HTML5 y HTML semántico ----------

    def test_doctype_html5_and_lang(self):
        self.assertTrue(self.parser.doctype, "Falta <!DOCTYPE html>")
        self.assertIn("html", self.parser.doctype.lower())
        self.assertEqual(self.parser.html_lang, "es",
                         "<html lang> debe estar definido y no vacío")

    def test_required_sections_and_semantic_structure(self):
        self.assertIn("<header>", self.html)
        self.assertIn("<main>", self.html)
        self.assertIn("<footer", self.html)
        self.assertIn("<nav>", self.html)
        self.assertIn("<h1>", self.html)
        for section_id in ("sobre-mi", "habilidades", "contacto",
                           "toggleHabilidades", "listaHabilidades"):
            self.assertIn(section_id, self.parser.ids)

    def test_single_h1_and_heading_order(self):
        self.assertEqual(self.parser.headings.count("h1"), 1,
                         "Debe existir exactamente un <h1>")
        levels = {"h1": 1, "h2": 2, "h3": 3, "h4": 4}
        last = 0
        for tag in self.parser.headings:
            level = levels[tag]
            self.assertLessEqual(level, last + 1,
                                 f"Encabezado saltado: <{tag}> tras nivel {last}")
            last = level

    def test_no_tables_for_layout(self):
        self.assertFalse(self.parser.uses_table,
                         "No se deben usar tablas para maquetar el sitio")

    def test_navigation_targets_exist(self):
        targets = {link["href"][1:] for link in self.parser.links
                   if link["href"].startswith("#")}
        self.assertTrue(targets.issubset(self.parser.ids))

    def test_local_assets_exist_and_images_are_described(self):
        for source, alt in self.parser.images:
            self.assertTrue((ROOT / source).is_file(),
                            f"No existe la imagen: {source}")
            self.assertTrue(alt.strip(),
                            f"Falta alt en la imagen: {source}")
        for source in self.parser.scripts:
            self.assertTrue((ROOT / source).is_file(),
                            f"No existe el script: {source}")

    def test_interaction_hooks_are_present(self):
        self.assertIn('getElementById("toggleHabilidades")', self.javascript)
        self.assertIn('getElementById("listaHabilidades")', self.javascript)
        self.assertIn('classList.toggle("oculto")', self.javascript)
        self.assertRegex(self.styles, r"\.oculto\s*\{\s*display:\s*none\s*;")

    # ---------- Accesibilidad y ARIA ----------

    def test_aria_accessible_names(self):
        for button in self.parser.buttons:
            name = (button["text"] or button["attrs"].get("aria-label")
                    or button["attrs"].get("title"))
            self.assertTrue(name, "Todo <button> necesita un nombre accesible")
        for link in self.parser.links:
            name = (link["text"] or link["aria-label"] or link["title"])
            self.assertTrue(name, f"Enlace sin nombre accesible: {link['href']}")

    def test_aria_references_exist(self):
        for attr, refs in self.parser.aria_references.items():
            for ref in refs:
                self.assertIn(ref, self.parser.ids,
                              f"{attr} apunta a un id inexistente: #{ref}")

    def test_aria_expanded_is_boolean(self):
        for button in self.parser.buttons:
            value = button["attrs"].get("aria-expanded")
            if value is not None:
                self.assertIn(value, {"true", "false"},
                              "aria-expanded debe ser true o false")

    def test_toggle_button_declares_state(self):
        toggle = [b for b in self.parser.buttons
                  if b["attrs"].get("id") == "toggleHabilidades"]
        self.assertEqual(len(toggle), 1, "Falta el botón toggleHabilidades")
        self.assertEqual(toggle[0]["attrs"].get("aria-controls"),
                         "listaHabilidades")
        self.assertEqual(toggle[0]["attrs"].get("aria-expanded"), "false")
        self.assertIn('setAttribute("aria-expanded"', self.javascript)

    def test_focus_visible_styles_defined(self):
        self.assertRegex(self.styles, r"(:focus-visible|:focus)")
        self.assertRegex(self.styles, r"outline")

    # ---------- Enlaces externos seguros ----------

    def _external_links(self):
        return [link for link in self.parser.links
                if link["href"].startswith(("http://", "https://"))]

    def test_external_links_use_https_only(self):
        for link in self._external_links():
            self.assertTrue(link["href"].startswith("https://"),
                            f"Enlace externo sin HTTPS: {link['href']}")

    def test_no_dangerous_schemes(self):
        for link in self.parser.links:
            href = link["href"].strip().lower()
            for scheme in SCHEMES_PELIGROSOS:
                self.assertFalse(href.startswith(scheme),
                                 f"Esquema peligroso en: {link['href']}")

    def test_blank_target_requires_noopener(self):
        for link in self.parser.links:
            if link["target"] == "_blank":
                rel = {part.strip().lower() for part in link["rel"].split()}
                self.assertIn("noopener", rel,
                              f"target=_blank sin rel=noopener: {link['href']}")

    def test_youtube_links_are_trusted_and_https(self):
        youtube = [link for link in self._external_links()
                   if "youtube" in link["href"] or "youtu.be" in link["href"]]
        for link in youtube:
            parsed = urlparse(link["href"])
            host = (parsed.hostname or "").lower()
            self.assertIn(host, YOUTUBE_DOMAINS,
                          f"Enlace de YouTube hacia dominio no permitido: "
                          f"{link['href']}")
            self.assertEqual(parsed.scheme, "https",
                             f"Enlace de YouTube sin HTTPS: {link['href']}")
            self.assertFalse(parsed.username or parsed.password,
                             f"URL de YouTube con credenciales incrustadas: "
                             f"{link['href']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)