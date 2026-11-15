"""Property test for price lookup."""

from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from qayta.bot import lookup_price

_KEYS = st.sampled_from(["pet", "glass", "paper"])
_JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=10),
    lambda children: st.lists(children, max_size=2),
    max_leaves=3,
)
_DATES = st.dates().map(lambda d: d.isoformat()) | st.text(max_size=12)
_RECORD = st.fixed_dictionaries(
    {},
    optional={
        "material": _KEYS | st.text(max_size=8) | _JSON,
        "price_som_per_kg": st.floats() | st.integers() | _JSON,
        "source": st.text(max_size=10) | _JSON,
        "date": _DATES | _JSON,
    },
)


@given(prices=st.lists(_RECORD, max_size=8), key=_KEYS | st.text(max_size=8))
def test_lookup_price_returns_none_or_complete_record(prices: list[dict], key: str) -> None:
    """**Validates: Requirements 8.1**"""
    result = lookup_price(prices, key)
    if result is None:
        return
    assert set(result) == {"material", "price_som_per_kg", "source", "date"}
    assert result["material"] == key
    assert isinstance(result["price_som_per_kg"], (int, float)) and result["price_som_per_kg"] > 0
    assert isinstance(result["source"], str) and result["source"].strip()
    assert isinstance(result["date"], str)
    date.fromisoformat(result["date"])
