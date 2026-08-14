from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.traces import render_corpus_callosum_svg


class CorpusCallosumPaletteTests(unittest.TestCase):
    def test_background_and_magenta_cells_have_distinct_svg_colors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "trace.svg"
            render_corpus_callosum_svg(
                output_path,
                ((0, 6), (6, 0)),
                ((6, 0), (0, 6)),
                "identity",
                {"events": []},
            )
            svg = output_path.read_text(encoding="utf-8")

        self.assertIn('fill="#111827"', svg)
        self.assertIn('fill="#d946ef"', svg)


if __name__ == "__main__":
    unittest.main()
