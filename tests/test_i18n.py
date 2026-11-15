"""Tests for qayta.i18n — translation helper.

Validates: Requirements 3.1, 3.2, 3.3, 3.4
"""

import re
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from qayta.i18n import _STRINGS, t

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOCALES_DIR = Path(__file__).parent.parent / "locales"


def _placeholders(template: str) -> set[str]:
    """Return the set of named placeholder keys used in *template*, e.g. ``{'name', 'tips'}``."""
    return set(re.findall(r"\{(\w+)\}", template))


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_known_key_returns_correct_string_en() -> None:
    """A known key in English returns the expected translated string."""
    result = t("tip.rinse", "en")
    assert result == "Rinse clean"


def test_known_key_returns_correct_string_uz() -> None:
    """A known key in Uzbek returns a non-empty string that is not the key itself."""
    result = t("mat.PET_1", "uz")
    assert result and result != "mat.PET_1"


def test_known_key_returns_correct_string_ru() -> None:
    """A known key in Russian returns a non-empty string that is not the key itself."""
    result = t("mat.GLASS", "ru")
    assert result == "Стекло"


def test_unknown_language_falls_back_to_english() -> None:
    """A language code that is not loaded falls back to the English translation."""
    result_unknown = t("tip.dry", "fr")
    result_en = t("tip.dry", "en")
    assert result_unknown == result_en


def test_unknown_language_falls_back_to_english_kz() -> None:
    """Another unsupported language also falls back to English."""
    result = t("mat.PAPER", "kz")
    assert result == "Paper"


def test_missing_key_returns_key_itself() -> None:
    """If a key does not exist in any locale, the key string is returned unchanged."""
    result = t("does.not.exist", "en")
    assert result == "does.not.exist"


def test_placeholder_substitution() -> None:
    """photo.result template is formatted correctly with all required placeholders."""
    result = t("photo.result", "en", name="Glass", status="♻️ Recyclable", tips="• Rinse clean")
    assert "Glass" in result
    assert "♻️ Recyclable" in result
    assert "• Rinse clean" in result


def test_lang_changed_placeholder() -> None:
    """lang.changed uses the {lang_name} placeholder in all locales."""
    for lang in ("uz", "ru", "en"):
        result = t("lang.changed", lang, lang_name="English")
        assert "English" in result


def test_all_locales_have_identical_keys() -> None:
    """All three locale files must contain exactly the same set of keys (Requirement 3.2)."""
    keys_uz = set(_STRINGS["uz"].keys())
    keys_ru = set(_STRINGS["ru"].keys())
    keys_en = set(_STRINGS["en"].keys())
    assert keys_uz == keys_en, f"uz vs en diff: {keys_uz.symmetric_difference(keys_en)}"
    assert keys_ru == keys_en, f"ru vs en diff: {keys_ru.symmetric_difference(keys_en)}"


def test_all_expected_material_keys_present() -> None:
    """All 13 material keys are present in every locale."""
    expected_materials = {
        "mat.PET_1", "mat.HDPE_2", "mat.PP_5", "mat.GLASS", "mat.PAPER",
        "mat.CARDBOARD", "mat.ALUMINIUM", "mat.STEEL", "mat.BATTERIES",
        "mat.EWASTE", "mat.TEXTILES", "mat.ORGANIC", "mat.MIXED",
    }
    for lang in ("uz", "ru", "en"):
        missing = expected_materials - set(_STRINGS[lang].keys())
        assert not missing, f"Missing material keys in {lang}: {missing}"


def test_all_expected_tip_keys_present() -> None:
    """All tip keys defined in the spec are present in every locale."""
    expected_tips = {
        "tip.rinse", "tip.remove_cap", "tip.flatten", "tip.dry",
        "tip.separate_pages", "tip.remove_staples", "tip.discharge",
        "tip.handle_safely", "tip.remove_batteries", "tip.keep_whole",
        "tip.bag_separately", "tip.no_preparation",
    }
    for lang in ("uz", "ru", "en"):
        missing = expected_tips - set(_STRINGS[lang].keys())
        assert not missing, f"Missing tip keys in {lang}: {missing}"


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


# Build a strategy that yields (key, lang, kwargs) triples where kwargs contains
# dummy string values for every placeholder present in the English template.
_all_keys = sorted(_STRINGS["en"].keys())
_supported_langs = ("uz", "ru", "en")


@settings(max_examples=200)
@given(
    key=st.sampled_from(_all_keys),
    lang=st.sampled_from(_supported_langs),
    placeholder_value=st.text(min_size=0, max_size=50),
)
def test_formatting_never_raises(key: str, lang: str, placeholder_value: str) -> None:
    """For every locale key in every language, formatting with correct placeholder names never raises.

    Validates: Requirements 3.4
    """
    # Derive expected placeholder names from the English template
    en_template = _STRINGS["en"].get(key, key)
    placeholders = _placeholders(en_template)
    kwargs = {name: placeholder_value for name in placeholders}

    # Should not raise regardless of the placeholder value content
    result = t(key, lang, **kwargs)
    assert isinstance(result, str)


@settings(max_examples=100)
@given(lang=st.sampled_from(_supported_langs))
def test_all_keys_return_non_empty_string(lang: str) -> None:
    """Every key in every locale returns a non-empty string when called without placeholders.

    Keys that have placeholders may contain literal braces in the output, which is fine —
    the important thing is that a string is returned and no exception is raised.
    """
    for key in _STRINGS["en"].keys():
        # Only call t() without kwargs for keys that have no placeholders
        en_template = _STRINGS["en"].get(key, "")
        if not _placeholders(en_template):
            result = t(key, lang)
            assert result, f"Empty result for key={key!r}, lang={lang!r}"
