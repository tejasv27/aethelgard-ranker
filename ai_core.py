"""
Aethelgard AI Core — LLM-Powered Dynamic Weight Generation
===========================================================

Uses Google Gemini 2.5 Flash with strict structured output schemas
to analyze a Job Description and dynamically distribute scoring weights
across the 7 deterministic axes. Falls back gracefully to hardcoded
defaults if the API is unavailable.

V5 OMEGA: Uses native google-genai structured output (response_schema)
for guaranteed JSON conformance, eliminating parse failures from
language drift or malformed responses.

Author: Team Aethelgard
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv

# Load .env file for local development (no-op in Docker/HF Spaces)
load_dotenv()

log = logging.getLogger("aethelgard.ai_core")

# ---------------------------------------------------------------------------
# Default weights (identical to rank.py module-level constants)
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS: dict[str, float] = {
    "title_career": 0.28,
    "skills": 0.22,
    "experience": 0.15,
    "behavioral": 0.15,
    "location": 0.08,
    "education": 0.05,
    "career_quality": 0.07,
}

# The 7 axes and their descriptions for the LLM prompt
AXIS_DESCRIPTIONS: dict[str, str] = {
    "title_career": "Title Alignment & Career Trajectory — how closely the candidate's job titles and career arc match the role",
    "skills": "Technical Skill Quality — depth and relevance of AI/ML skills (not just keyword count)",
    "experience": "Experience Fit — years of experience match against the JD's stated range",
    "behavioral": "Behavioral & Platform Activity — engagement signals, response rate, availability",
    "location": "Location Preference — geographic match for on-site/hybrid requirements",
    "education": "Education Quality — institution tier and field relevance",
    "career_quality": "Career Ownership & Product Engineering Depth — product company vs. services background",
}

# ---------------------------------------------------------------------------
# Structured Output Schema for Gemini
# ---------------------------------------------------------------------------
WEIGHT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title_career": {
            "type": "INTEGER",
            "description": "Points for title alignment and career trajectory (2-40)",
        },
        "skills": {
            "type": "INTEGER",
            "description": "Points for technical skill quality and depth (2-40)",
        },
        "experience": {
            "type": "INTEGER",
            "description": "Points for years of experience fit (2-40)",
        },
        "behavioral": {
            "type": "INTEGER",
            "description": "Points for behavioral and platform activity signals (2-40)",
        },
        "location": {
            "type": "INTEGER",
            "description": "Points for location and geographic preference (2-40)",
        },
        "education": {
            "type": "INTEGER",
            "description": "Points for education quality and relevance (2-40)",
        },
        "career_quality": {
            "type": "INTEGER",
            "description": "Points for career ownership and product engineering depth (2-40)",
        },
    },
    "required": [
        "title_career", "skills", "experience",
        "behavioral", "location", "education", "career_quality",
    ],
}

# ---------------------------------------------------------------------------
# Meta-Prompt for Gemini (used with structured output)
# ---------------------------------------------------------------------------
STRUCTURED_PROMPT = """You are an expert AI Hiring Strategist. Analyze this Job Description and distribute exactly 100 points across 7 scoring dimensions based on the JD's priorities.

The 7 dimensions:
1. title_career: {title_career}
2. skills: {skills}
3. experience: {experience}
4. behavioral: {behavioral}
5. location: {location}
6. education: {education}
7. career_quality: {career_quality}

RULES:
- Distribute exactly 100 total points.
- Each dimension: minimum 2, maximum 40.
- Higher points = more important for this JD.

JOB DESCRIPTION:
{jd_text}"""

# Legacy free-text prompt (fallback if structured output fails)
FALLBACK_PROMPT = """You are an expert AI Hiring Strategist. Given a Job Description, distribute exactly 100 points across 7 scoring dimensions.

The 7 dimensions are:
1. title_career: {title_career}
2. skills: {skills}
3. experience: {experience}
4. behavioral: {behavioral}
5. location: {location}
6. education: {education}
7. career_quality: {career_quality}

RULES:
- Distribute exactly 100 total points across all 7 dimensions.
- Each dimension must get at least 2 points and at most 40 points.
- Respond with ONLY a valid JSON object. No markdown, no explanation.

Example: {{"title_career": 28, "skills": 22, "experience": 15, "behavioral": 15, "location": 8, "education": 5, "career_quality": 7}}

JOB DESCRIPTION:
{jd_text}

JSON:"""


def _validate_and_normalize(data: dict[str, Any]) -> dict[str, float] | None:
    """
    Validate weight distribution and normalize to sum to 1.0.
    Returns None if validation fails.
    """
    required_keys = set(DEFAULT_WEIGHTS.keys())

    # Check all 7 keys exist
    if not required_keys.issubset(set(data.keys())):
        missing = required_keys - set(data.keys())
        log.warning(f"Missing keys in weight response: {missing}")
        return None

    # Validate all values are positive numbers
    for key in required_keys:
        if not isinstance(data[key], (int, float)):
            log.warning(f"Non-numeric value for {key}: {data[key]}")
            return None
        if data[key] < 0:
            log.warning(f"Negative value for {key}: {data[key]}")
            return None

    # Clamp outliers to [2, 40] range
    for key in required_keys:
        data[key] = max(2, min(40, data[key]))

    # Normalize to sum to 1.0
    total = sum(data[key] for key in required_keys)
    if total <= 0:
        log.warning(f"Total weight is zero or negative: {total}")
        return None

    normalized = {key: round(data[key] / total, 4) for key in required_keys}

    # Fix rounding error
    norm_sum = sum(normalized.values())
    if abs(norm_sum - 1.0) > 0.001:
        diff = 1.0 - norm_sum
        max_key = max(normalized, key=normalized.get)
        normalized[max_key] = round(normalized[max_key] + diff, 4)

    return normalized


def _parse_freetext_response(response_text: str) -> dict[str, float] | None:
    """Parse a free-text LLM response into weights. Legacy fallback path."""
    text = response_text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[^}]+\}", text)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return None
        else:
            return None

    return _validate_and_normalize(data)


def generate_dynamic_weights(jd_text: str) -> tuple[dict[str, float], str]:
    """
    Use Gemini 2.5 Flash to generate dynamic scoring weights from a JD.

    Strategy (V5 OMEGA):
    1. First attempt: Use structured output schema for guaranteed JSON
    2. Fallback: Free-text prompt with regex parsing
    3. Final fallback: Return hardcoded defaults

    Args:
        jd_text: The raw Job Description text.

    Returns:
        (weights_dict, status_message) — weights normalized to sum=1.0,
        and a status string.
    """
    # Support both GEMINI_API_KEY (.env / HF Secrets) and legacy GOOGLE_API_KEY
    api_key = (
        os.environ.get("GEMINI_API_KEY", "")
        or os.environ.get("GOOGLE_API_KEY", "")
    ).strip()

    if not api_key:
        log.info("GEMINI_API_KEY not set. Using default weights.")
        return DEFAULT_WEIGHTS.copy(), "fallback: no API key"

    if not jd_text or len(jd_text.strip()) < 20:
        log.info("JD text too short for meaningful analysis. Using defaults.")
        return DEFAULT_WEIGHTS.copy(), "fallback: JD too short"

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = STRUCTURED_PROMPT.format(
            jd_text=jd_text[:3000],
            **AXIS_DESCRIPTIONS,
        )

        # ── Attempt 1: Structured output with response_schema ─────────
        try:
            log.info("Attempting structured output generation...")
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WEIGHT_SCHEMA,
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
            )

            data = json.loads(response.text)
            weights = _validate_and_normalize(data)

            if weights:
                log.info(f"Structured output weights: {weights}")
                return weights, "ai_generated (structured)"

            log.warning("Structured output validation failed. Trying fallback...")

        except Exception as e:
            log.warning(f"Structured output failed: {e}. Trying free-text fallback...")

        # ── Attempt 2: Free-text prompt fallback ──────────────────────
        try:
            fallback_prompt = FALLBACK_PROMPT.format(
                jd_text=jd_text[:3000],
                **AXIS_DESCRIPTIONS,
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=fallback_prompt,
            )

            weights = _parse_freetext_response(response.text)
            if weights:
                log.info(f"Free-text fallback weights: {weights}")
                return weights, "ai_generated (freetext)"

            log.warning("Free-text parsing also failed. Using defaults.")

        except Exception as e:
            log.warning(f"Free-text fallback also failed: {e}")

        return DEFAULT_WEIGHTS.copy(), "fallback: all attempts failed"

    except ImportError:
        log.warning("google-genai not installed. Using default weights.")
        return DEFAULT_WEIGHTS.copy(), "fallback: google-genai not installed"

    except Exception as e:
        log.warning(f"Gemini API error: {e}. Using default weights.")
        return DEFAULT_WEIGHTS.copy(), f"fallback: {type(e).__name__}"
