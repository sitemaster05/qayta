"""Tests for src/qayta/vision.py.

All Gemini calls are mocked — no network access required.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qayta.materials import CATALOGUE
from qayta.vision import (
    CONFIDENCE_THRESHOLD,
    ClassificationResult,
    MaterialKey,
    Vision,
    VisionUnavailable,
    decide,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CATALOGUE_KEYS = list(CATALOGUE.keys())


def _make_vision(fake_client: MagicMock) -> Vision:
    """Create a Vision instance with an injected fake client (no real API call)."""
    vision = Vision.__new__(Vision)
    vision._model = "gemini-flash-lite-latest"
    vision._client = fake_client
    return vision


def _make_response(text: str) -> MagicMock:
    """Return a mock Gemini response with the given .text."""
    resp = MagicMock()
    resp.text = text
    return resp


def _valid_json(material: str = "PET_1", confidence: float = 0.9, reason: str = "Clear PET bottle") -> str:
    return json.dumps({"material": material, "confidence": confidence, "reason": reason})


# ---------------------------------------------------------------------------
# Unit tests — classify()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_valid_response_returns_result() -> None:
    """A well-formed JSON response yields a ClassificationResult."""
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(return_value=_make_response(_valid_json()))
    vision = _make_vision(fake_client)

    result = await vision.classify(b"fake-image", "image/jpeg")

    assert isinstance(result, ClassificationResult)
    assert result.material.value == "PET_1"
    assert result.confidence == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_classify_malformed_json_returns_none() -> None:
    """Malformed JSON in the response → None (not an exception)."""
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(return_value=_make_response("not json at all"))
    vision = _make_vision(fake_client)

    result = await vision.classify(b"fake-image", "image/jpeg")

    assert result is None


@pytest.mark.asyncio
async def test_classify_unknown_material_key_returns_none() -> None:
    """A valid JSON with an unknown material key fails Pydantic validation → None."""
    payload = json.dumps({"material": "PLASTIC_99", "confidence": 0.8, "reason": "Unknown"})
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(return_value=_make_response(payload))
    vision = _make_vision(fake_client)

    result = await vision.classify(b"fake-image", "image/jpeg")

    assert result is None


@pytest.mark.asyncio
async def test_classify_mocked_429_raises_vision_unavailable() -> None:
    """An HTTP 429 / quota error raises VisionUnavailable."""
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(side_effect=Exception("Error 429 quota exceeded"))
    vision = _make_vision(fake_client)

    with pytest.raises(VisionUnavailable):
        await vision.classify(b"fake-image", "image/jpeg")


@pytest.mark.asyncio
async def test_classify_timeout_raises_vision_unavailable() -> None:
    """asyncio.TimeoutError propagates as VisionUnavailable."""
    fake_client = MagicMock()

    async def _slow(*_args: object, **_kwargs: object) -> None:
        await asyncio.sleep(100)

    fake_client.aio.models.generate_content = _slow
    vision = _make_vision(fake_client)

    # Patch asyncio.timeout so it fires immediately
    with patch("qayta.vision.asyncio.timeout") as mock_timeout:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=TimeoutError)
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_timeout.return_value = cm

        with pytest.raises(VisionUnavailable):
            await vision.classify(b"fake-image", "image/jpeg")


@pytest.mark.asyncio
async def test_classify_network_error_raises_vision_unavailable() -> None:
    """A generic network/connection error raises VisionUnavailable."""
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(side_effect=ConnectionError("Network unreachable"))
    vision = _make_vision(fake_client)

    with pytest.raises(VisionUnavailable):
        await vision.classify(b"fake-image", "image/jpeg")


@pytest.mark.asyncio
async def test_classify_missing_response_text_returns_none() -> None:
    """If response.text is missing/None, classify returns None gracefully."""
    fake_client = MagicMock()
    resp = MagicMock()
    resp.text = None
    fake_client.aio.models.generate_content = AsyncMock(return_value=resp)
    vision = _make_vision(fake_client)

    result = await vision.classify(b"fake-image", "image/jpeg")

    assert result is None


# ---------------------------------------------------------------------------
# Unit tests — decide()
# ---------------------------------------------------------------------------


def test_decide_none_returns_none() -> None:
    assert decide(None) is None


def test_decide_unclear_returns_none() -> None:
    result = ClassificationResult(material=MaterialKey.UNCLEAR, confidence=0.99, reason="Unclear")  # type: ignore[attr-defined]
    assert decide(result) is None


def test_decide_low_confidence_returns_none() -> None:
    """confidence = 0.59 is below the 0.6 threshold → None."""
    result = ClassificationResult(material=MaterialKey.PET_1, confidence=0.59, reason="Low")  # type: ignore[attr-defined]
    assert decide(result) is None


def test_decide_threshold_boundary_returns_material() -> None:
    """confidence = 0.6 exactly is at the threshold → return the material."""
    result = ClassificationResult(material=MaterialKey.PET_1, confidence=0.6, reason="OK")  # type: ignore[attr-defined]
    material = decide(result)
    assert material is not None
    assert material.key == "PET_1"


def test_decide_high_confidence_returns_correct_material() -> None:
    result = ClassificationResult(material=MaterialKey.GLASS, confidence=0.95, reason="Glass bottle")  # type: ignore[attr-defined]
    material = decide(result)
    assert material is not None
    assert material.key == "GLASS"


def test_decide_all_catalogue_keys_resolve() -> None:
    """Every catalogue key with confidence 1.0 returns the correct material."""
    for key in _CATALOGUE_KEYS:
        mat_key = MaterialKey(key)  # type: ignore[call-arg]
        result = ClassificationResult(material=mat_key, confidence=1.0, reason="Test")
        material = decide(result)
        assert material is not None, f"Expected material for key {key}"
        assert material.key == key


# ---------------------------------------------------------------------------
# Property tests — decide()
# ---------------------------------------------------------------------------


@given(
    key=st.sampled_from(_CATALOGUE_KEYS),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(max_examples=200)
def test_decide_property_confidence_threshold(key: str, confidence: float) -> None:
    """Validates: Requirements — for any catalogue key and confidence in [0,1],
    decide returns the entry iff confidence >= CONFIDENCE_THRESHOLD.
    """
    mat_key = MaterialKey(key)  # type: ignore[call-arg]
    result = ClassificationResult(material=mat_key, confidence=confidence, reason="Property test")
    material = decide(result)

    if confidence >= CONFIDENCE_THRESHOLD:
        assert material is not None
        assert material.key == key
    else:
        assert material is None
