"""Tests for the material catalogue (materials.py).

Validates:
- CATALOGUE contains exactly the 13 expected keys.
- Every entry has between 1 and 3 preparation tips.
- Property: name_i18n and all tip keys resolve to non-empty strings in all three locales.
"""

import hypothesis.strategies as st
from hypothesis import given

from qayta.i18n import t
from qayta.materials import CATALOGUE, Material

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    "PET_1",
    "HDPE_2",
    "PP_5",
    "GLASS",
    "PAPER",
    "CARDBOARD",
    "ALUMINIUM",
    "STEEL",
    "BATTERIES",
    "EWASTE",
    "TEXTILES",
    "ORGANIC",
    "MIXED",
}

SUPPORTED_LANGS = ("uz", "ru", "en")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_catalogue_has_exactly_13_keys() -> None:
    """CATALOGUE must contain exactly the 13 documented material keys."""
    assert set(CATALOGUE.keys()) == EXPECTED_KEYS


def test_every_entry_has_one_to_three_tips() -> None:
    """Every material must have between 1 and 3 preparation tips (inclusive)."""
    for key, material in CATALOGUE.items():
        tip_count = len(material.tips)
        assert 1 <= tip_count <= 3, (
            f"Material {key!r} has {tip_count} tips; expected 1–3."
        )


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


@given(st.sampled_from(sorted(CATALOGUE.keys())))
def test_material_keys_resolve_in_all_locales(material_key: str) -> None:
    """For every material, name_i18n and all tip keys resolve to non-empty strings.

    Validates: Requirements — material catalogue i18n completeness.
    """
    material: Material = CATALOGUE[material_key]

    for lang in SUPPORTED_LANGS:
        # Display name must translate to a non-empty, non-fallback string.
        name_translation = t(material.name_i18n, lang)
        assert name_translation, (
            f"name_i18n {material.name_i18n!r} resolved to empty string for lang={lang!r}"
        )
        # t() falls back to the key itself when the key is missing; catch that case.
        assert name_translation != material.name_i18n, (
            f"name_i18n {material.name_i18n!r} is untranslated (returned the key) for lang={lang!r}"
        )

        # Every tip key must also resolve to a non-empty, non-fallback string.
        for tip_key in material.tips:
            tip_translation = t(tip_key, lang)
            assert tip_translation, (
                f"Tip {tip_key!r} resolved to empty string for lang={lang!r} (material={material_key!r})"
            )
            assert tip_translation != tip_key, (
                f"Tip {tip_key!r} is untranslated (returned the key) for lang={lang!r} "
                f"(material={material_key!r})"
            )
