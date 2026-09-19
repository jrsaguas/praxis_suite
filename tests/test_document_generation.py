import unittest
import tempfile
from pathlib import Path

from convert import convert_with_python_docx, convert_markdown_to_doc, sanitize_xml


class DocumentRegressionTests(unittest.TestCase):
    def test_xml_control_characters_are_removed(self):
        self.assertEqual(sanitize_xml("A\x00B\x0bC"), "ABC")

    def test_docx_contains_equation_and_code(self):
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / "sample.md"
            out = Path(td) / "sample.docx"
            md.write_text("# Prueba\n\nTexto $x^2$\n\n$$\n\\frac{1}{2}\n$$\n\n```python\nprint(1)\n```\n", encoding="utf-8")
            ok, msg = convert_with_python_docx(str(md), str(out))
            self.assertTrue(ok, msg)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)

    def test_docx_omml_contains_math_structure_not_literal_latex(self):
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / "math.md"
            out = Path(td) / "math.docx"
            md.write_text(
                "# Matemática\n\n"
                "$x^2$\n\n"
                "$\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$\n",
                encoding="utf-8",
            )
            ok, msg = convert_with_python_docx(str(md), str(out))
            self.assertTrue(ok, msg)

            import zipfile
            from xml.etree import ElementTree as ET

            with zipfile.ZipFile(out) as zf:
                document_xml = zf.read("word/document.xml").decode("utf-8")

            self.assertIn("oMath", document_xml)
            self.assertIn("<m:f>", document_xml)
            self.assertIn("<m:rad>", document_xml)
            self.assertIn("<m:sSup>", document_xml)
            self.assertNotIn(r"\frac", document_xml)
            self.assertNotIn(r"\sqrt", document_xml)
            self.assertNotIn(r"\pm", document_xml)
            ET.fromstring(document_xml)

    def test_legacy_doc_is_generated(self):
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / "sample.md"
            out = Path(td) / "sample.doc"
            md.write_text("# Prueba\n\nContenido & seguridad\n", encoding="utf-8")
            ok, msg = convert_markdown_to_doc(str(md), str(out), title="Prueba")
            self.assertTrue(ok, msg)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 100)

if __name__ == "__main__":
    unittest.main()
