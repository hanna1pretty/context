"""Intelligence keyboards (spec section 12): brand, styleguide,
people, company. People actions carry the privacy warning in the
message text (formatters/messages.py), not in the button."""
from __future__ import annotations

from ..callbacks.intelligence import (
    brand_lookup, brand_search, company_search, intelligence_start,
    people_enrich, people_search, styleguide,
)
from ..callbacks.navigation import nav_screen
from .common import _mk, with_back_home


def intelligence_menu():
    return _mk(with_back_home([
        [("Brand Lookup", brand_lookup()), ("Brand Search", brand_search())],
        [("Styleguide", styleguide()), ("People Search", people_search())],
        [("People Enrich", people_enrich()), ("Company Search", company_search())],
    ]))


def brand_menu():
    return _mk(with_back_home([
        [("Brand Lookup", brand_lookup()), ("Brand Search", brand_search())],
        [("Styleguide", styleguide())],
    ]))


def people_menu():
    return _mk(with_back_home([
        [("People Search", people_search()), ("People Enrich", people_enrich())],
    ]))


def company_menu():
    return _mk(with_back_home([
        [("Company Search", company_search())],
    ]))


def intelligence_result_keyboard():
    return _mk(with_back_home([
        [("Cari Lagi", intelligence_start()), ("Kembali ke Intel", nav_screen("intelligence"))],
    ]))
