import unittest
import tempfile
from pathlib import Path

from convert import convert_with_python_docx, convert_markdown_to_doc, sanitize_xml


class DocumentRegressionTests(unittest.TestCase):
    def test_xml_control_characters_are_removed(self):
        self.assertEqual(sanitize_xml("A\\x00B\\x0bC"), "ABC")

    def test_docx_contains_equation_and_code(self):
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / "sample.md"
            out = Path(td) / "sample.docx"
            md.write_text("# Prueba\\n\\nTexto $x^2$\\n\\n$$\\n\\\\frac{1}{2}\\n$$\\n\\n```python\\nprint(1)\\n```\\n", encoding="utf-8")
            ok, msg = convert_with_python_docx(str(md), str(out))
            self.assertTrue(ok, msg)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)

    def test_legacy_doc_is_generated(self):
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / "sample.md"
            out = Path(td) / "sample.doc"
            md.write_text("# Prueba\\n\\nContenido & seguridad\\n", encoding="utf-8")
            ok, msg = convert_markdown_to_doc(str(md), str(out), title="Prueba")
            self.assertTrue(ok, msg)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 100)

if __name__ == "__main__":
    unittest.main()