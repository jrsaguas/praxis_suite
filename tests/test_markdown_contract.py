import unittest
from markdown_contract import assemble_markdown, validate_canonical_markdown

class MarkdownContractTests(unittest.TestCase):
    def test_preserves_block_math_for_pandoc(self):
        md = assemble_markdown(["Teoría", "$$\\\\frac{1}{2}$$"])
        result = validate_canonical_markdown(md)
        self.assertTrue(result["preserves_dollar_delimiters"])
        self.assertEqual(result["math_block_count"], 1)
        self.assertTrue(result["has_raw_latex"])

if __name__ == "__main__":
    unittest.main()