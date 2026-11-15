"""Gemini-powered photo classification for Qayta.

Exposes:
- ``ClassificationResult`` — Pydantic model for the structured JSON response.
- ``VisionUnavailable`` — raised on quota/network/timeout errors.
- ``Vision`` — thin async wrapper around the Gemini client (create once, reuse).
- ``decide()`` — pure function that maps a ``ClassificationResult`` to a ``Material``.
"""

import asyncio
import json
import logging
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from qayta.materials import CATALOGUE, Material

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

# Build the enum dynamically so it always matches CATALOGUE exactly.
MaterialKey = Enum("MaterialKey", {k: k for k in [*CATALOGUE, "UNCLEAR"]}, type=str)  # type: ignore[misc]


class ClassificationResult(BaseModel):
    """Structured response returned by Gemini for a recycling photo."""

    material: MaterialKey  # type: ignore[valid-type]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=200)


class VisionUnavailable(Exception):
    """Raised when Gemini is unreachable: quota (429), timeout, or network failure.

    The bot replies with ``photo.busy`` and asks the user to try again later.
    """


# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------

_ALLOWED_KEYS = ", ".join([*CATALOGUE, "UNCLEAR"])

CLASSIFICATION_PROMPT: str = f"""You are a recycling-material classifier for Qayta, a Telegram bot serving
users in Uzbekistan and Central Asia.

Examine the photo and identify the primary recyclable material shown.

Allowed material values (pick **exactly one**):
{_ALLOWED_KEYS}

Rules:
- Use UNCLEAR when:
  • The photo shows a person or people.
  • The photo is a screenshot or a document (text on screen).
  • The photo contains several clearly different material types and you cannot determine the dominant one.
  • Your confidence would be below 0.6.
- confidence must be a float between 0.0 and 1.0.
- reason must be a single sentence (≤ 200 characters) explaining your classification.

Return ONLY a JSON object in this exact shape (no markdown fences, no extra keys):
{{"material": "<KEY>", "confidence": <float>, "reason": "<sentence>"}}
"""

# ---------------------------------------------------------------------------
# Confidence threshold
# ---------------------------------------------------------------------------

CONFIDENCE_THRESHOLD: float = 0.6

# ---------------------------------------------------------------------------
# Vision class
# ---------------------------------------------------------------------------

try:
    from google import genai
    from google.genai.types import GenerateContentConfig, Part

    _GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover — only missing in bare envs
    _GENAI_AVAILABLE = False


class Vision:
    """Wraps the Gemini client; create **one** instance and reuse it.

    Args:
        api_key: Google Gemini API key.
        model:   Gemini model name (default ``"gemini-flash-lite-latest"``).
    """

    def __init__(self, api_key: str, model: str = "gemini-flash-lite-latest") -> None:
        if not _GENAI_AVAILABLE:  # pragma: no cover
            raise ImportError("google-genai is not installed")
        self._model = model
        self._client: genai.Client = genai.Client(api_key=api_key)  # type: ignore[name-defined]

    async def classify(self, image_bytes: bytes, mime_type: str) -> ClassificationResult | None:
        """Classify a photo and return the structured result.

        Args:
            image_bytes: Raw image bytes (JPEG, PNG, WebP, …).
            mime_type:   MIME type string, e.g. ``"image/jpeg"``.

        Returns:
            A :class:`ClassificationResult` on success, or ``None`` when the
            response is malformed / the material key is unknown.

        Raises:
            VisionUnavailable: On HTTP 429, :class:`asyncio.TimeoutError`, or
                any other network-level failure.
        """
        try:
            async with asyncio.timeout(30):
                image_part = Part.from_bytes(data=image_bytes, mime_type=mime_type)  # type: ignore[name-defined]
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=[image_part, CLASSIFICATION_PROMPT],
                    config=GenerateContentConfig(  # type: ignore[name-defined]
                        response_mime_type="application/json",
                        response_schema=ClassificationResult,
                        temperature=0,
                    ),
                )
        except TimeoutError as exc:
            logger.warning("Gemini classify timed out")
            raise VisionUnavailable("Request timed out") from exc
        except Exception as exc:  # noqa: BLE001
            # Catch HTTP errors (including 429) and any network failures.
            exc_str = str(exc)
            if "429" in exc_str or "quota" in exc_str.lower() or "rate" in exc_str.lower():
                logger.warning("Gemini quota/rate-limit hit: %s", exc_str)
                raise VisionUnavailable("Quota exceeded") from exc
            # Generic network / API error
            logger.warning("Gemini classify failed: %s", exc_str)
            raise VisionUnavailable(exc_str) from exc

        # Parse the structured response text.
        try:
            text = response.text
            return ClassificationResult.model_validate_json(text)
        except (ValidationError, json.JSONDecodeError, AttributeError) as exc:
            logger.warning("Gemini response parse error: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------


def decide(result: ClassificationResult | None) -> Material | None:
    """Map a :class:`ClassificationResult` to a :class:`Material`, or ``None``.

    Returns ``None`` when:
    - *result* is ``None`` (parse error or no response).
    - The material is ``UNCLEAR``.
    - The material key is not present in :data:`~qayta.materials.CATALOGUE`.
    - Confidence is below :data:`CONFIDENCE_THRESHOLD` (0.6).

    Args:
        result: The classification produced by :meth:`Vision.classify`.

    Returns:
        The matching :class:`~qayta.materials.Material` entry, or ``None``.
    """
    if result is None:
        return None
    if result.material.value == "UNCLEAR":
        return None
    key = result.material.value
    if key not in CATALOGUE:
        return None
    if result.confidence < CONFIDENCE_THRESHOLD:
        return None
    return CATALOGUE[key]
