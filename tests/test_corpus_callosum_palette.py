from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.traces import _operator_label, render_corpus_callosum_svg


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

    def test_long_structural_operator_labels_remain_readable(self) -> None:
        self.assertEqual(
            _operator_label("central_separator_cellwise_combine(axis=vertical,table=0:0:0)"),
            "central-separator merge",
        )
        self.assertEqual(
            _operator_label("cross_separator_quadrant_reflection_stamp"),
            "cross-quadrant reflection",
        )
        self.assertEqual(
            _operator_label(
                "adjacent_bilateral_cellwise_combine(axis=vertical,table=0:0:0)"
            ),
            "bilateral-panel merge",
        )
        self.assertEqual(
            _operator_label("distinct_nonbackground_scale"),
            "nonbackground scale",
        )


if __name__ == "__main__":
    unittest.main()
