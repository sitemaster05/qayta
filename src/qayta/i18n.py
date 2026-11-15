"""Internationalisation helpers.

Locale files are loaded once at module import time from the ``locales/`` directory
at the project root (two levels above this file: src/qayta/ → src/ → project root).
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve the locales directory relative to this file's location.
_LOCALES_DIR: Path = Path(__file__).parent.parent.parent / "locales"

_SUPPORTED_LANGS: tuple[str, ...] = ("uz", "ru", "en")

_STRINGS: dict[str, dict[str, str]] = {}


def _load_locales() -> None:
    """Load all locale JSON files into ``_STRINGS`` at import time."""
    for lang in _SUPPORTED_LANGS:
        locale_file = _LOCALES_DIR / f"{lang}.json"
        if not locale_file.exists():
            expected = [str(_LOCALES_DIR / f"{code}.json") for code in _SUPPORTED_LANGS]
            raise FileNotFoundError(
                f"Missing locale file: {locale_file}. Expected all of {expected}."
            )
        with locale_file.open(encoding="utf-8") as fh:
            _STRINGS[lang] = json.load(fh)
        logger.debug("Loaded %d translation keys for lang=%s", len(_STRINGS[lang]), lang)


_load_locales()


def t(key: str, lang: str, **kwargs: object) -> str:
    """Return the formatted translation string for *key* in *lang*.

    Falls back to English if *lang* is not available. Falls back to *key* itself
    if the key is not found in the chosen locale (so nothing ever crashes).

    Args:
        key:    Dotted translation key, e.g. ``"photo.result"``.
        lang:   Two-letter language code: ``"uz"``, ``"ru"`` or ``"en"``.
        **kwargs: Named placeholders passed to ``str.format``.

    Returns:
        The translated and formatted string.
    """
    strings = _STRINGS.get(lang) or _STRINGS["en"]
    template = strings.get(key) or _STRINGS["en"].get(key, key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        logger.warning("Missing placeholder %s for key %r (lang=%s)", exc, key, lang)
        return template
