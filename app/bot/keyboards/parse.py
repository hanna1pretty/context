"""Parse keyboards (spec section 11). File info is shown escaped in the
message text; no server path ever appears in a button or callback."""
from __future__ import annotations

from ..callbacks.parse import (
    parse_export, parse_ocr, parse_output, parse_pages, parse_start,
    parse_upload, parse_url, parse_view,
)
from .common import _mk, with_back_home


def parse_menu():
    return _mk(with_back_home([
        [("Upload File", parse_upload())],
        [("Gunakan URL File", parse_url())],
        [("Markdown Output", parse_output("markdown")), ("HTML Output", parse_output("html"))],
        [("OCR jika tersedia", parse_ocr()), ("Batas Halaman", parse_pages())],
    ]))


def parse_result_keyboard():
    """After a file is accepted: view/export the parsed output, or start
    over. Never a raw-JSON dump in chat (see formatters: Lihat JSON /
    Download / Salin are the export actions)."""
    return _mk(with_back_home([
        [("Lihat Hasil", parse_view()), ("Export", parse_export())],
        [("Parse File Lain", parse_start())],
    ]))
