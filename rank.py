#!/usr/bin/env python3
"""
Aethelgard — Hybrid Deterministic + Semantic Intelligence Pipeline
=================================================================

Ranks 100,000 candidates against a Senior AI Engineer JD using a
multi-signal weighted scoring pipeline with an optional semantic
re-ranking pass. CPU-only, no network calls, deterministic core.

Architecture:
    1. Stream-parse candidates from gzipped JSONL (low memory footprint)
    2. Extract features: experience, title, skills, career, location, signals
    3. Compute composite score via weighted deterministic formula
    4. Detect and penalize honeypot candidates
    5. (Optional) Semantic re-ranking of top 500 via sentence-transformers
    6. Sort, take top 100, generate explainable reasoning, write CSV + details JSON

Usage:
    python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv
    python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv --semantic

Author: Team Aethelgard
License: MIT
"""

from __future__ import annotations

import argparse
import csv
import gzip
import heapq
import json
import logging
import math
import re
import sys
import time
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("aethelgard")

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

# ── Experience sweet spot (JD says 5-9 years, ideal is 6-8) ──────────────
IDEAL_EXP_MIN: float = 5.0
IDEAL_EXP_MAX: float = 9.0
SWEET_SPOT_MIN: float = 6.0
SWEET_SPOT_MAX: float = 8.0
EXP_HARD_MIN: float = 2.0   # Below this, candidate is almost certainly unfit
EXP_HARD_MAX: float = 20.0  # Above this, likely overqualified / not hands-on

# ── Weight allocations for composite score ────────────────────────────────
# These sum to 1.0 and reflect the JD's stated priorities
W_TITLE_CAREER: float = 0.28     # Title alignment + career trajectory (highest)
W_SKILLS: float = 0.22           # Skill match quality (not just count)
W_EXPERIENCE: float = 0.15       # Years of experience fit
W_BEHAVIORAL: float = 0.15       # Redrob engagement signals
W_LOCATION: float = 0.08         # Tier-1 city / India / relocation
W_EDUCATION: float = 0.05        # Tier-1/2 institution bonus
W_CAREER_QUALITY: float = 0.07   # Product engineering & ownership depth

# ── Title relevance tiers ─────────────────────────────────────────────────
# Titles are grouped by how closely they match "Senior AI Engineer" role
TITLE_TIER_1: set[str] = {
    "ai engineer", "senior ai engineer", "staff ai engineer",
    "machine learning engineer", "senior machine learning engineer",
    "ml engineer", "senior ml engineer", "staff ml engineer",
    "applied scientist", "senior applied scientist",
    "research engineer", "senior research engineer",
    "nlp engineer", "senior nlp engineer",
    "deep learning engineer", "ranking engineer",
    "search engineer", "retrieval engineer",
    "recommendation engineer", "relevance engineer",
}

TITLE_TIER_2: set[str] = {
    "data scientist", "senior data scientist", "staff data scientist",
    "lead data scientist", "principal data scientist",
    "software engineer", "senior software engineer",
    "backend engineer", "senior backend engineer",
    "platform engineer", "senior platform engineer",
    "full stack engineer", "senior full stack engineer",
    "tech lead", "engineering manager",
    "junior ml engineer", "junior ai engineer",
    "data engineer", "senior data engineer",
    "analytics engineer", "mlops engineer",
}

TITLE_TIER_3: set[str] = {
    "product manager", "technical product manager",
    "project manager", "program manager",
    "devops engineer", "sre engineer",
    "cloud engineer", "infrastructure engineer",
    "solutions architect", "technical architect",
    "consultant", "technical consultant",
    "business analyst", "systems analyst",
}

# Titles that are explicit disqualifiers per JD
TITLE_DISQUALIFY: set[str] = {
    "marketing manager", "hr manager", "human resources manager",
    "sales executive", "sales manager", "account manager",
    "content writer", "copywriter", "technical writer",
    "graphic designer", "ui designer", "ux designer",
    "accountant", "finance manager", "cfo",
    "operations manager", "supply chain manager",
    "customer support", "customer success",
    "civil engineer", "mechanical engineer",
    "electrical engineer", "chemical engineer",
    "teacher", "professor", "lecturer",
}

# ── Core AI/ML skills from the JD ────────────────────────────────────────
# Weighted by relevance to the specific JD requirements
SKILLS_CRITICAL: dict[str, float] = {
    # "Things you absolutely need" from the JD
    "embeddings": 1.0,
    "sentence-transformers": 1.0,
    "sentence transformers": 1.0,
    "vector search": 1.0,
    "vector database": 1.0,
    "vector databases": 1.0,
    "retrieval": 1.0,
    "information retrieval": 1.0,
    "ranking": 1.0,
    "learning to rank": 1.0,
    "search": 0.9,
    "elasticsearch": 0.9,
    "opensearch": 0.9,
    "pinecone": 1.0,
    "weaviate": 1.0,
    "qdrant": 1.0,
    "milvus": 1.0,
    "faiss": 1.0,
    "hybrid search": 1.0,
    "bm25": 0.9,
    "ndcg": 0.9,
    "mrr": 0.9,
    "evaluation": 0.8,
    "a/b testing": 0.8,
    "ab testing": 0.8,
}

SKILLS_IMPORTANT: dict[str, float] = {
    # "Things we'd like you to have" + strong ML foundations
    "python": 0.7,
    "nlp": 0.8,
    "natural language processing": 0.8,
    "llm": 0.8,
    "large language models": 0.8,
    "fine-tuning": 0.8,
    "fine-tuning llms": 0.8,
    "fine tuning": 0.8,
    "lora": 0.7,
    "qlora": 0.7,
    "peft": 0.7,
    "rag": 0.9,
    "retrieval augmented generation": 0.9,
    "langchain": 0.5,  # JD warns against framework-only people
    "llamaindex": 0.6,
    "transformers": 0.8,
    "huggingface": 0.7,
    "hugging face": 0.7,
    "pytorch": 0.7,
    "tensorflow": 0.6,
    "deep learning": 0.7,
    "machine learning": 0.7,
    "recommendation systems": 0.8,
    "recommendation engine": 0.8,
    "xgboost": 0.6,
    "lightgbm": 0.6,
    "catboost": 0.6,
    "bert": 0.7,
    "gpt": 0.6,
    "openai": 0.5,
    "prompt engineering": 0.5,
}

SKILLS_ADJACENT: dict[str, float] = {
    # Adjacent but valuable skills
    "docker": 0.3,
    "kubernetes": 0.3,
    "aws": 0.3,
    "gcp": 0.3,
    "azure": 0.3,
    "sql": 0.3,
    "postgresql": 0.3,
    "redis": 0.3,
    "kafka": 0.3,
    "spark": 0.3,
    "airflow": 0.3,
    "mlflow": 0.4,
    "wandb": 0.4,
    "weights & biases": 0.4,
    "bentoml": 0.4,
    "fastapi": 0.4,
    "flask": 0.3,
    "git": 0.2,
    "ci/cd": 0.3,
    "data engineering": 0.4,
    "feature engineering": 0.5,
    "statistical modeling": 0.4,
    "data science": 0.4,
    "computer vision": 0.2,  # JD explicitly says not a fit unless NLP too
    "image classification": 0.1,
    "speech recognition": 0.1,
    "tts": 0.1,
    "gans": 0.2,
}

# ── Large enterprise outsourcing firms (JD flags limited ownership) ───────
LARGE_ENTERPRISE_OUTSOURCERS: set[str] = {
    "tcs", "tata consultancy services", "tata consultancy",
    "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "hcl", "hcl technologies",
    "tech mahindra", "l&t infotech", "lti", "ltimindtree",
    "mindtree", "mphasis", "hexaware",
    "persistent systems", "zensar", "cyient",
    "niit technologies", "coforge",
    "virtusa", "birlasoft", "sonata software",
    "happiest minds", "mastek", "atos",
    "dxc technology", "dxc", "cgi", "ntt data",
    "ibm global services", "deloitte consulting",
    "ey", "ernst & young", "kpmg", "pwc",
    "pricewaterhousecoopers",
}

# ── Tier-1 Indian cities (JD: Pune/Noida preferred, Tier-1 welcome) ──────
TIER1_CITIES: set[str] = {
    "pune", "noida", "delhi", "new delhi", "delhi ncr",
    "gurgaon", "gurugram", "mumbai", "bangalore", "bengaluru",
    "hyderabad", "chennai",
}

# Broader India locations that are acceptable
INDIA_CITIES: set[str] = TIER1_CITIES | {
    "kolkata", "ahmedabad", "jaipur", "lucknow", "chandigarh",
    "indore", "nagpur", "coimbatore", "kochi", "thiruvananthapuram",
    "bhopal", "patna", "visakhapatnam", "vadodara", "surat",
    "guwahati", "ranchi", "bhubaneswar", "dehradun", "mysore",
    "mangalore", "trivandrum",
}

# Preferred cities get a bonus
PREFERRED_CITIES: set[str] = {"pune", "noida", "delhi ncr", "new delhi", "delhi", "gurgaon", "gurugram"}


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Lowercase and strip whitespace for consistent matching."""
    return text.strip().lower()


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dictionary keys."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a float to [lo, hi]."""
    return max(lo, min(hi, value))


def days_since(date_str: str, reference_date: date) -> int:
    """Calculate days between a date string and a reference date."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (reference_date - d).days
    except (ValueError, TypeError):
        return 9999  # Treat unparseable dates as very old


# ---------------------------------------------------------------------------
# Feature Extraction
# ---------------------------------------------------------------------------

def extract_features(candidate: dict, today: date) -> dict[str, Any]:
    """
    Extract all scoring-relevant features from a candidate record.

    Returns a flat dictionary of features used by the scoring functions.
    This separation of extraction from scoring ensures testability and
    makes the scoring logic transparent.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    skills_raw = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    education = candidate.get("education", [])

    # ── Basic profile features ────────────────────────────────────────
    candidate_id: str = candidate.get("candidate_id", "UNKNOWN")
    years_exp: float = profile.get("years_of_experience", 0.0)
    current_title: str = normalize(profile.get("current_title", ""))
    current_company: str = normalize(profile.get("current_company", ""))
    headline: str = normalize(profile.get("headline", ""))
    summary: str = normalize(profile.get("summary", ""))
    location: str = normalize(profile.get("location", ""))
    country: str = normalize(profile.get("country", ""))

    # ── Skill extraction with deduplication ────────────────────────────
    skill_names: list[str] = []
    skill_details: list[dict] = []
    for s in skills_raw:
        name = normalize(s.get("name", ""))
        if name:
            skill_names.append(name)
            skill_details.append({
                "name": name,
                "proficiency": normalize(s.get("proficiency", "beginner")),
                "endorsements": s.get("endorsements", 0),
                "duration_months": s.get("duration_months", 0),
            })

    # ── Career history features ───────────────────────────────────────
    career_entries: list[dict] = []
    for entry in career:
        career_entries.append({
            "company": normalize(entry.get("company", "")),
            "title": normalize(entry.get("title", "")),
            "duration_months": entry.get("duration_months", 0),
            "is_current": entry.get("is_current", False),
            "industry": normalize(entry.get("industry", "")),
            "company_size": entry.get("company_size", ""),
            "description": normalize(entry.get("description", "")),
        })

    # ── Education features ────────────────────────────────────────────
    edu_tiers: list[str] = []
    edu_fields: list[str] = []
    for e in education:
        tier = normalize(e.get("tier", "unknown"))
        field = normalize(e.get("field_of_study", ""))
        edu_tiers.append(tier)
        edu_fields.append(field)

    # ── Behavioral signals ────────────────────────────────────────────
    open_to_work: bool = signals.get("open_to_work_flag", False)
    response_rate: float = signals.get("recruiter_response_rate", 0.0)
    notice_days: int = signals.get("notice_period_days", 180)
    last_active_str: str = signals.get("last_active_date", "2020-01-01")
    last_active_days: int = days_since(last_active_str, today)
    github_score: float = signals.get("github_activity_score", -1)
    profile_completeness: float = signals.get("profile_completeness_score", 0)
    interview_completion: float = signals.get("interview_completion_rate", 0.0)
    offer_acceptance: float = signals.get("offer_acceptance_rate", -1)
    avg_response_hours: float = signals.get("avg_response_time_hours", 999)
    willing_to_relocate: bool = signals.get("willing_to_relocate", False)
    preferred_work_mode: str = normalize(signals.get("preferred_work_mode", ""))
    saved_by_recruiters: int = signals.get("saved_by_recruiters_30d", 0)
    profile_views: int = signals.get("profile_views_received_30d", 0)
    search_appearances: int = signals.get("search_appearance_30d", 0)
    verified_email: bool = signals.get("verified_email", False)
    verified_phone: bool = signals.get("verified_phone", False)
    linkedin_connected: bool = signals.get("linkedin_connected", False)
    skill_assessments: dict = signals.get("skill_assessment_scores", {})

    return {
        "candidate_id": candidate_id,
        "years_exp": years_exp,
        "current_title": current_title,
        "current_company": current_company,
        "headline": headline,
        "summary": summary,
        "location": location,
        "country": country,
        "skill_names": skill_names,
        "skill_details": skill_details,
        "skill_count": len(skill_names),
        "career_entries": career_entries,
        "edu_tiers": edu_tiers,
        "edu_fields": edu_fields,
        "open_to_work": open_to_work,
        "response_rate": response_rate,
        "notice_days": notice_days,
        "last_active_days": last_active_days,
        "last_active_str": last_active_str,
        "github_score": github_score,
        "profile_completeness": profile_completeness,
        "interview_completion": interview_completion,
        "offer_acceptance": offer_acceptance,
        "avg_response_hours": avg_response_hours,
        "willing_to_relocate": willing_to_relocate,
        "preferred_work_mode": preferred_work_mode,
        "saved_by_recruiters": saved_by_recruiters,
        "profile_views": profile_views,
        "search_appearances": search_appearances,
        "verified_email": verified_email,
        "verified_phone": verified_phone,
        "linkedin_connected": linkedin_connected,
        "skill_assessments": skill_assessments,
        # Raw profile/summary for reasoning generation
        "raw_profile": candidate.get("profile", {}),
        "raw_career": candidate.get("career_history", []),
    }


# ---------------------------------------------------------------------------
# Honeypot Detection
# ---------------------------------------------------------------------------

def detect_honeypot(features: dict[str, Any]) -> tuple[bool, str]:
    """
    Detect honeypot candidates with subtly impossible profiles.

    Honeypot signals (from the spec):
    - >15 skills but <2 years experience
    - Response rate near 0 (≤0.02) combined with other suspicious signals
    - "Expert" proficiency in many skills with 0 duration
    - Impossible career timelines

    Returns:
        (is_honeypot: bool, reason: str)
    """
    reasons: list[str] = []
    penalty_score: int = 0

    years_exp = features["years_exp"]
    skill_count = features["skill_count"]
    skill_details = features["skill_details"]
    response_rate = features["response_rate"]
    career_entries = features["career_entries"]

    # ── Check 1: Too many skills for too little experience ────────────
    # Spec explicitly calls this out: >15 skills but <2 years
    if skill_count > 15 and years_exp < 2.0:
        reasons.append(f"HONEYPOT: {skill_count} skills with only {years_exp:.1f}y exp")
        penalty_score += 100

    # ── Check 2: Near-zero response rate ──────────────────────────────
    # Spec: "response rates near 0"
    if response_rate <= 0.02:
        reasons.append(f"HONEYPOT: near-zero response rate ({response_rate:.2f})")
        penalty_score += 50

    # ── Check 3: Expert in many skills with 0 or near-0 duration ──────
    expert_zero_duration = sum(
        1 for s in skill_details
        if s["proficiency"] == "expert" and s["duration_months"] < 3
    )
    if expert_zero_duration >= 5:
        reasons.append(f"HONEYPOT: {expert_zero_duration} expert skills with <3mo duration")
        penalty_score += 80

    # ── Check 4: Skill count wildly inconsistent with experience ──────
    # Even legitimate senior engineers rarely list >20 skills
    if skill_count > 20 and years_exp < 4.0:
        reasons.append(f"HONEYPOT: {skill_count} skills at {years_exp:.1f}y exp")
        penalty_score += 60

    # ── Check 5: Many advanced/expert proficiencies with few endorsements ──
    high_prof_low_endorse = sum(
        1 for s in skill_details
        if s["proficiency"] in ("advanced", "expert")
        and s["endorsements"] == 0
        and s["duration_months"] < 6
    )
    if high_prof_low_endorse >= 8:
        reasons.append(f"HONEYPOT: {high_prof_low_endorse} adv/expert skills with 0 endorsements and <6mo")
        penalty_score += 70

    # ── Check 6: Impossible career timeline ───────────────────────────
    # Total career duration exceeds stated years_of_experience by >50%
    total_career_months = sum(e["duration_months"] for e in career_entries)
    if years_exp > 0 and total_career_months > (years_exp * 12 * 2.0):
        reasons.append(
            f"HONEYPOT: career months ({total_career_months}) >> "
            f"stated exp ({years_exp:.1f}y = {years_exp * 12:.0f}mo)"
        )
        penalty_score += 40

    is_honeypot = penalty_score >= 50
    reason = "; ".join(reasons) if reasons else ""
    return is_honeypot, reason


# ---------------------------------------------------------------------------
# Scoring Components
# ---------------------------------------------------------------------------

def score_title_career(features: dict[str, Any]) -> float:
    """
    Score based on current title + career trajectory alignment.

    This is the HIGHEST-WEIGHTED component because the JD is very specific:
    the role is "Senior AI Engineer" and the JD explicitly says keyword
    matching on skills alone is a trap. Title + career trajectory is the
    strongest signal of genuine fit.

    Returns: 0.0 to 1.0
    """
    title = features["current_title"]
    headline = features["headline"]
    career_entries = features["career_entries"]

    # ── Current title scoring ─────────────────────────────────────────
    title_score: float = 0.0

    if title in TITLE_TIER_1:
        title_score = 1.0
    elif title in TITLE_TIER_2:
        title_score = 0.65
    elif title in TITLE_TIER_3:
        title_score = 0.25
    elif title in TITLE_DISQUALIFY:
        title_score = 0.0  # Hard zero for clearly non-technical roles
    else:
        # Unknown title — check headline for AI/ML signals
        ai_headline_terms = [
            "ai", "ml", "machine learning", "deep learning", "nlp",
            "data scientist", "research", "ranking", "search",
            "embeddings", "retrieval",
        ]
        headline_hits = sum(1 for t in ai_headline_terms if t in headline)
        title_score = min(0.5, headline_hits * 0.15)

    # ── Career trajectory scoring ─────────────────────────────────────
    # Look at the arc: are they moving toward AI/ML roles?
    trajectory_score: float = 0.0
    ai_role_months: int = 0
    total_months: int = 0

    for entry in career_entries:
        months = entry["duration_months"]
        total_months += months
        entry_title = entry["title"]
        entry_desc = entry["description"]

        # Check if the role involved AI/ML work
        is_ai_role = (
            entry_title in TITLE_TIER_1
            or entry_title in TITLE_TIER_2
            or any(term in entry_desc for term in [
                "machine learning", "ml model", "deep learning",
                "embedding", "retrieval", "ranking", "search",
                "nlp", "natural language", "recommendation",
                "neural", "transformer", "vector", "fine-tun",
                "classification", "regression", "clustering",
            ])
        )
        if is_ai_role:
            ai_role_months += months

    if total_months > 0:
        ai_fraction = ai_role_months / total_months
        trajectory_score = min(1.0, ai_fraction * 1.2)  # Slight boost

    # ── Check for product-building signals in career descriptions ─────
    product_signals = 0
    for entry in career_entries:
        desc = entry["description"]
        if any(term in desc for term in [
            "shipped", "deployed", "production", "end-to-end",
            "real users", "scale", "a/b test", "online",
            "latency", "throughput", "serving", "inference",
            "pipeline", "system design",
        ]):
            product_signals += 1

    product_bonus = min(0.15, product_signals * 0.05)

    # Composite: 55% title, 35% trajectory, 10% product signals
    return clamp(title_score * 0.55 + trajectory_score * 0.35 + product_bonus)


def score_skills(features: dict[str, Any]) -> float:
    """
    Score skill match quality — NOT just count.

    The JD warns: "The right answer is NOT find candidates whose skills
    section contains the most AI keywords." So we:
    1. Weight skills by JD relevance tier
    2. Apply a trust multiplier based on endorsements + duration
    3. Penalize keyword stuffing (many skills, no depth)

    Returns: 0.0 to 1.0
    """
    skill_details = features["skill_details"]
    skill_names_set = set(features["skill_names"])
    summary = features["summary"]
    skill_assessments = features["skill_assessments"]

    if not skill_details:
        return 0.0

    weighted_score: float = 0.0
    max_possible: float = 0.0

    # ── Match skills against JD requirements ──────────────────────────
    # Check all three tiers
    all_jd_skills: dict[str, float] = {}
    all_jd_skills.update(SKILLS_ADJACENT)
    all_jd_skills.update(SKILLS_IMPORTANT)
    all_jd_skills.update(SKILLS_CRITICAL)  # Critical overwrites if duplicated

    matched_critical: int = 0
    matched_important: int = 0

    for skill in skill_details:
        name = skill["name"]
        proficiency = skill["proficiency"]
        endorsements = skill["endorsements"]
        duration = skill["duration_months"]

        # Find the best JD match for this skill
        jd_weight = all_jd_skills.get(name, 0.0)

        # Also check partial matches for multi-word skill names
        if jd_weight == 0.0:
            for jd_skill, w in all_jd_skills.items():
                if jd_skill in name or name in jd_skill:
                    jd_weight = max(jd_weight, w * 0.8)  # Partial match discount

        if jd_weight <= 0.0:
            continue

        # ── Trust multiplier ──────────────────────────────────────────
        # A skill with high endorsements + long duration is more credible
        prof_mult = {"beginner": 0.3, "intermediate": 0.6, "advanced": 0.85, "expert": 1.0}
        trust = prof_mult.get(proficiency, 0.3)

        # Duration credibility: 12+ months is credible, 0 months is suspicious
        if duration >= 24:
            trust *= 1.0
        elif duration >= 12:
            trust *= 0.85
        elif duration >= 6:
            trust *= 0.6
        elif duration > 0:
            trust *= 0.35
        else:
            trust *= 0.1  # Zero duration = very suspicious

        # Endorsement credibility bonus
        if endorsements >= 10:
            trust = min(1.0, trust * 1.15)
        elif endorsements >= 5:
            trust = min(1.0, trust * 1.05)

        # Check if they have a Redrob assessment for this skill
        if name in skill_assessments or any(
            sn in skill_assessments for sn in [name.title(), name.upper()]
        ):
            # Assessment exists — score matters
            for assess_name, assess_score in skill_assessments.items():
                if normalize(assess_name) == name:
                    if assess_score >= 70:
                        trust = min(1.0, trust * 1.2)
                    elif assess_score < 40:
                        trust *= 0.7  # Low assessment hurts credibility
                    break

        weighted_score += jd_weight * trust

        # Track critical/important matches
        if name in SKILLS_CRITICAL:
            matched_critical += 1
        elif name in SKILLS_IMPORTANT:
            matched_important += 1

    # Also scan summary text for skill mentions (some candidates describe
    # skills in summary without listing them formally)
    for jd_skill, w in SKILLS_CRITICAL.items():
        if jd_skill in summary and jd_skill not in skill_names_set:
            weighted_score += w * 0.3  # Lower weight for mention-only

    # ── Normalize ─────────────────────────────────────────────────────
    # Max theoretical score if candidate had all critical + important skills
    max_possible = sum(SKILLS_CRITICAL.values()) + sum(SKILLS_IMPORTANT.values()) * 0.5
    raw_score = weighted_score / max_possible if max_possible > 0 else 0.0

    # ── Keyword stuffing penalty ──────────────────────────────────────
    # JD explicitly warns about this trap
    skill_count = features["skill_count"]
    years_exp = features["years_exp"]
    if skill_count > 15 and years_exp < 5:
        # Suspicious: too many skills for experience level
        raw_score *= 0.5
    elif skill_count > 20:
        # Even senior people listing >20 skills is suspicious
        raw_score *= 0.8

    # ── Critical skill bonus ──────────────────────────────────────────
    # Having multiple critical skills matters disproportionately
    if matched_critical >= 4:
        raw_score = min(1.0, raw_score * 1.3)
    elif matched_critical >= 2:
        raw_score = min(1.0, raw_score * 1.15)

    return clamp(raw_score)


def score_experience(features: dict[str, Any]) -> float:
    """
    Score years of experience fit against JD requirements.

    JD says 5-9 years, ideal 6-8 years. Below 2 or above 20 are strong
    negatives. This is a shaped curve, not a simple threshold.

    Returns: 0.0 to 1.0
    """
    years = features["years_exp"]

    if years < EXP_HARD_MIN:
        return 0.05  # Nearly zero but not exactly (some prodigies exist)

    if SWEET_SPOT_MIN <= years <= SWEET_SPOT_MAX:
        return 1.0  # Perfect range

    if IDEAL_EXP_MIN <= years <= IDEAL_EXP_MAX:
        return 0.9  # Good range

    if years < IDEAL_EXP_MIN:
        # Linear ramp from EXP_HARD_MIN to IDEAL_EXP_MIN
        return 0.05 + 0.85 * (years - EXP_HARD_MIN) / (IDEAL_EXP_MIN - EXP_HARD_MIN)

    if years <= 12:
        # Mild penalty for slightly over
        return 0.9 - (years - IDEAL_EXP_MAX) * 0.1

    if years <= EXP_HARD_MAX:
        # Steeper penalty: likely moved to management per JD
        return max(0.2, 0.6 - (years - 12) * 0.05)

    # Beyond 20 years — JD says they want hands-on coders
    return 0.1


def score_behavioral(features: dict[str, Any]) -> float:
    """
    Score Redrob behavioral/engagement signals.

    The JD says: "A perfect-on-paper candidate who hasn't logged in for
    6 months and has a 5% recruiter response rate is, for hiring purposes,
    not actually available. Down-weight them appropriately."

    This computes an "Availability Float" combining:
    - Open to work flag
    - Recruiter response rate
    - Notice period penalty
    - Recency of activity
    - Profile completeness

    Returns: 0.0 to 1.0
    """
    open_to_work = features["open_to_work"]
    response_rate = features["response_rate"]
    notice_days = features["notice_days"]
    last_active_days = features["last_active_days"]
    github_score = features["github_score"]
    profile_completeness = features["profile_completeness"]
    interview_completion = features["interview_completion"]
    avg_response_hours = features["avg_response_hours"]
    saved_by_recruiters = features["saved_by_recruiters"]
    verified_email = features["verified_email"]
    linkedin_connected = features["linkedin_connected"]

    # ── Availability Float ────────────────────────────────────────────
    # Open to work is a strong multiplier
    otw_mult = 1.0 if open_to_work else 0.5

    # Response rate — the JD emphasizes this heavily
    if response_rate >= 0.7:
        rr_score = 1.0
    elif response_rate >= 0.4:
        rr_score = 0.7 + (response_rate - 0.4) * 1.0
    elif response_rate >= 0.1:
        rr_score = 0.3 + (response_rate - 0.1) * 1.33
    elif response_rate > 0.02:
        rr_score = 0.15
    else:
        rr_score = 0.0  # Near-zero = honeypot signal or truly unavailable

    # ── Notice period penalty ─────────────────────────────────────────
    # JD: "We'd love sub-30-day notice. Can buy out up to 30 days.
    #      30+ day candidates still in scope but bar gets higher."
    if notice_days <= 30:
        notice_score = 1.0
    elif notice_days <= 60:
        notice_score = 0.8
    elif notice_days <= 90:
        notice_score = 0.6
    elif notice_days <= 120:
        notice_score = 0.4
    else:
        notice_score = 0.2

    # ── Recency of activity ───────────────────────────────────────────
    if last_active_days <= 7:
        recency_score = 1.0
    elif last_active_days <= 30:
        recency_score = 0.9
    elif last_active_days <= 90:
        recency_score = 0.7
    elif last_active_days <= 180:
        recency_score = 0.4  # "hasn't logged in for 6 months"
    else:
        recency_score = 0.15  # Very stale

    # ── Profile quality indicators ────────────────────────────────────
    quality_score: float = 0.0
    quality_count: int = 0

    # Profile completeness
    quality_score += profile_completeness / 100.0
    quality_count += 1

    # Interview completion rate
    if interview_completion > 0:
        quality_score += interview_completion
        quality_count += 1

    # Response time
    if avg_response_hours <= 24:
        quality_score += 1.0
    elif avg_response_hours <= 72:
        quality_score += 0.7
    elif avg_response_hours <= 168:
        quality_score += 0.4
    else:
        quality_score += 0.1
    quality_count += 1

    # GitHub activity (not required but positive signal)
    if github_score >= 50:
        quality_score += 0.3
    elif github_score >= 20:
        quality_score += 0.15
    # -1 means no GitHub; don't penalize

    # Verification signals
    if verified_email:
        quality_score += 0.1
    if linkedin_connected:
        quality_score += 0.1

    # Recruiter interest signals
    if saved_by_recruiters >= 5:
        quality_score += 0.2
    elif saved_by_recruiters >= 2:
        quality_score += 0.1

    quality_avg = quality_score / max(quality_count, 1)

    # ── Composite behavioral score ────────────────────────────────────
    # Availability: 35% response rate, 20% notice, 25% recency, 10% OTW, 10% quality
    availability = (
        rr_score * 0.35
        + notice_score * 0.20
        + recency_score * 0.25
        + otw_mult * 0.10
        + quality_avg * 0.10
    )

    return clamp(availability)


def score_location(features: dict[str, Any]) -> float:
    """
    Score location fit against JD requirements.

    JD: Pune/Noida-preferred, Tier-1 Indian cities welcome,
    outside India case-by-case, no visa sponsorship.

    Returns: 0.0 to 1.0
    """
    location = features["location"]
    country = features["country"]
    willing_to_relocate = features["willing_to_relocate"]
    preferred_work_mode = features["preferred_work_mode"]

    # Extract city from location string (often "City, State" format)
    city = location.split(",")[0].strip() if location else ""

    # ── City matching ─────────────────────────────────────────────────
    is_preferred = any(pc in city for pc in PREFERRED_CITIES)
    is_tier1 = any(tc in city for tc in TIER1_CITIES)
    is_india = any(ic in city for ic in INDIA_CITIES) or "india" in country

    if is_preferred:
        location_score = 1.0
    elif is_tier1:
        location_score = 0.85
    elif is_india:
        location_score = 0.65
    elif "india" in country:
        location_score = 0.55
    else:
        # International — JD says "case-by-case, no visa sponsorship"
        location_score = 0.25

    # ── Relocation willingness bonus ──────────────────────────────────
    if not is_preferred and willing_to_relocate:
        location_score = min(1.0, location_score + 0.15)

    # ── Work mode compatibility ───────────────────────────────────────
    # JD: "Hybrid — flexible cadence"
    if preferred_work_mode in ("hybrid", "flexible"):
        location_score = min(1.0, location_score + 0.05)
    elif preferred_work_mode == "remote" and not is_india:
        location_score *= 0.7  # Remote from outside India is harder

    return clamp(location_score)


def score_education(features: dict[str, Any]) -> float:
    """
    Score education quality. Light weight — the JD doesn't emphasize
    education, but tier-1 institutions are a positive signal.

    Returns: 0.0 to 1.0
    """
    edu_tiers = features["edu_tiers"]
    edu_fields = features["edu_fields"]

    if not edu_tiers:
        return 0.3  # No education listed — neutral

    # Best tier in education history
    tier_scores = {
        "tier_1": 1.0,
        "tier_2": 0.75,
        "tier_3": 0.5,
        "tier_4": 0.35,
        "unknown": 0.3,
    }
    best_tier = max(tier_scores.get(t, 0.3) for t in edu_tiers)

    # Relevant field bonus
    relevant_fields = {
        "computer science", "cs", "artificial intelligence", "ai",
        "machine learning", "data science", "statistics",
        "mathematics", "electrical engineering", "ece",
        "information technology", "it",
    }
    has_relevant_field = any(
        any(rf in f for rf in relevant_fields)
        for f in edu_fields
    )
    field_bonus = 0.15 if has_relevant_field else 0.0

    return clamp(best_tier * 0.7 + field_bonus + 0.15)  # Base 0.15 for having education


def score_career_quality(features: dict[str, Any]) -> float:
    """
    Score career quality based on product engineering depth.

    Preference for candidates demonstrating end-to-end ownership,
    autonomous technical contribution, and product engineering impact.
    Candidates with prior product-company experience are valued higher,
    as the JD emphasizes hands-on building over managed-service delivery.

    Returns: 0.0 to 1.0
    """
    career_entries = features["career_entries"]

    if not career_entries:
        return 0.2

    outsource_months: int = 0
    product_months: int = 0
    total_months: int = 0
    has_product_company: bool = False

    for entry in career_entries:
        months = entry["duration_months"]
        total_months += months
        company = entry["company"]

        if company in LARGE_ENTERPRISE_OUTSOURCERS:
            outsource_months += months
        else:
            product_months += months
            has_product_company = True

    if total_months == 0:
        return 0.3

    outsource_fraction = outsource_months / total_months

    # ── No product engineering exposure detected ─────────────────────
    if not has_product_company:
        return 0.15  # Limited end-to-end ownership signal

    # ── Score by product engineering depth ─────────────────────────────
    if outsource_fraction > 0.8:
        return 0.35  # Limited product ownership exposure
    elif outsource_fraction > 0.5:
        return 0.55  # Moderate product engineering depth
    elif outsource_fraction > 0.2:
        return 0.75  # Strong product engineering background
    else:
        return 0.95  # Deep product engineering & ownership track record


# ---------------------------------------------------------------------------
# Composite Scoring
# ---------------------------------------------------------------------------

def compute_composite_score(
    features: dict[str, Any],
    weight_schema: dict[str, float] | None = None,
) -> tuple[float, dict[str, float]]:
    """
    Compute the final deterministic composite score.

    Args:
        features: Extracted candidate features.
        weight_schema: Optional dynamic weights (must sum to ~1.0).
            Keys: title_career, skills, experience, behavioral,
                  location, education, career_quality.
            If None, uses the module-level default constants.

    Returns:
        (composite_score, component_scores_dict) — the composite and all
        individual components for reasoning generation.
    """
    # ── Resolve weights ───────────────────────────────────────────────
    if weight_schema is not None:
        w_title = weight_schema.get("title_career", W_TITLE_CAREER)
        w_skills = weight_schema.get("skills", W_SKILLS)
        w_exp = weight_schema.get("experience", W_EXPERIENCE)
        w_behav = weight_schema.get("behavioral", W_BEHAVIORAL)
        w_loc = weight_schema.get("location", W_LOCATION)
        w_edu = weight_schema.get("education", W_EDUCATION)
        w_career = weight_schema.get("career_quality", W_CAREER_QUALITY)
    else:
        w_title = W_TITLE_CAREER
        w_skills = W_SKILLS
        w_exp = W_EXPERIENCE
        w_behav = W_BEHAVIORAL
        w_loc = W_LOCATION
        w_edu = W_EDUCATION
        w_career = W_CAREER_QUALITY

    # ── Compute all components ────────────────────────────────────────
    s_title = score_title_career(features)
    s_skills = score_skills(features)
    s_exp = score_experience(features)
    s_behavioral = score_behavioral(features)
    s_location = score_location(features)
    s_education = score_education(features)
    s_career_q = score_career_quality(features)

    # ── Weighted sum ──────────────────────────────────────────────────
    composite = (
        w_title * s_title
        + w_skills * s_skills
        + w_exp * s_exp
        + w_behav * s_behavioral
        + w_loc * s_location
        + w_edu * s_education
        + w_career * s_career_q
    )

    # ── Honeypot penalty ──────────────────────────────────────────────
    is_honeypot, hp_reason = detect_honeypot(features)
    if is_honeypot:
        composite *= 0.01  # Crush to near-zero

    # ── Title disqualifier check ──────────────────────────────────────
    # If the current title is clearly non-technical AND they have no
    # AI/ML career history, apply a heavy penalty
    if features["current_title"] in TITLE_DISQUALIFY and s_title < 0.1:
        composite *= 0.15

    components = {
        "title_career": s_title,
        "skills": s_skills,
        "experience": s_exp,
        "behavioral": s_behavioral,
        "location": s_location,
        "education": s_education,
        "career_quality": s_career_q,
        "is_honeypot": 1.0 if is_honeypot else 0.0,
        "honeypot_reason": hp_reason,
    }

    return clamp(composite), components


# ---------------------------------------------------------------------------
# Reasoning Generation
# ---------------------------------------------------------------------------

def generate_reasoning(
    features: dict[str, Any],
    score: float,
    rank: int,
    components: dict[str, float],
) -> str:
    """
    Generate a 1-2 sentence explainable reasoning string using standard
    Python string formatting. NO LLM generation.

    The reasoning references specific facts from the candidate's profile
    and connects them to JD requirements, as required by Stage 4 review.
    """
    raw_profile = features["raw_profile"]
    title = raw_profile.get("current_title", "Unknown")
    company = raw_profile.get("current_company", "Unknown")
    years = features["years_exp"]
    location = raw_profile.get("location", "Unknown")

    # ── Identify strengths ────────────────────────────────────────────
    strengths: list[str] = []
    concerns: list[str] = []

    # Title/career
    if components["title_career"] >= 0.7:
        strengths.append(f"{title} role aligns well with Senior AI Engineer JD")
    elif components["title_career"] >= 0.4:
        strengths.append(f"some career relevance as {title}")
    else:
        concerns.append(f"current {title} role doesn't align with AI engineering")

    # Skills
    matched_skills: list[str] = []
    for skill in features["skill_details"]:
        name = skill["name"]
        if name in SKILLS_CRITICAL or name in SKILLS_IMPORTANT:
            matched_skills.append(name)

    if matched_skills:
        top_skills = matched_skills[:4]
        strengths.append(f"relevant skills: {', '.join(top_skills)}")

    if components["skills"] < 0.2:
        concerns.append("limited matching AI/ML skill set")

    # Experience
    if 5.0 <= years <= 9.0:
        strengths.append(f"{years:.1f}y experience fits 5-9y JD range")
    elif years < 3.0:
        concerns.append(f"only {years:.1f}y experience (JD needs 5-9y)")
    elif years > 12:
        concerns.append(f"{years:.1f}y may be overqualified; JD values hands-on coding")

    # Location
    city = location.split(",")[0].strip() if location else ""
    if components["location"] >= 0.85:
        strengths.append(f"located in {city}")
    elif components["location"] < 0.4:
        concerns.append(f"based in {location}, relocation uncertain")

    # Behavioral
    rr = features["response_rate"]
    notice = features["notice_days"]

    if rr < 0.1:
        concerns.append(f"very low response rate ({rr:.0%})")
    elif rr >= 0.6:
        strengths.append(f"strong engagement ({rr:.0%} response rate)")

    if notice > 90:
        concerns.append(f"{notice}-day notice period")

    # Career quality
    if components["career_quality"] < 0.3:
        concerns.append("limited product engineering or end-to-end ownership experience")
    elif components["career_quality"] >= 0.8:
        strengths.append("strong product-company background")

    # Honeypot
    if components.get("is_honeypot", 0.0) > 0:
        hp_reason = components.get("honeypot_reason", "suspicious profile")
        return f"FLAGGED: {hp_reason}. Profile excluded from genuine ranking."

    # ── Build the reasoning string ────────────────────────────────────
    parts: list[str] = []

    if strengths:
        parts.append("; ".join(strengths[:3]))

    if concerns:
        if rank <= 30:
            # Top candidates: mention concerns as caveats
            parts.append("minor concerns: " + "; ".join(concerns[:2]))
        elif rank <= 70:
            parts.append("concerns: " + "; ".join(concerns[:2]))
        else:
            parts.append("; ".join(concerns[:3]))

    reasoning = ". ".join(parts)

    # Ensure we stay within 1-2 sentences and add company context
    if len(reasoning) > 250:
        reasoning = reasoning[:247] + "..."

    if not reasoning:
        reasoning = (
            f"{title} at {company} with {years:.1f}y experience; "
            f"score {score:.3f} based on multi-signal evaluation."
        )

    return reasoning


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def open_candidates_file(filepath: str):
    """
    Open candidates file, supporting both .jsonl.gz and .jsonl formats.
    Returns a context manager yielding text lines.
    """
    path = Path(filepath)
    if path.suffix == ".gz" or filepath.endswith(".jsonl.gz"):
        return gzip.open(filepath, "rt", encoding="utf-8")
    else:
        return open(filepath, "r", encoding="utf-8")


# ---------------------------------------------------------------------------
# Semantic Re-Ranking Layer (Optional)
# ---------------------------------------------------------------------------

def _build_candidate_text(features: dict[str, Any]) -> str:
    """Build a text profile for semantic encoding from candidate features."""
    parts = []
    raw = features.get("raw_profile", {})
    title = raw.get("current_title", "")
    headline = raw.get("headline", "")
    summary = raw.get("summary", "")
    skills = ", ".join(features.get("skill_names", [])[:20])

    if title:
        parts.append(f"Current role: {title}")
    if headline:
        parts.append(headline)
    if summary:
        parts.append(summary[:300])
    if skills:
        parts.append(f"Skills: {skills}")

    # Add career descriptions
    for entry in features.get("career_entries", [])[:3]:
        desc = entry.get("description", "")
        if desc:
            parts.append(desc[:200])

    return ". ".join(parts)[:1000]  # Cap total length


JD_TEXT = (
    "Senior AI Engineer with expertise in embeddings, vector search, retrieval systems, "
    "ranking, learning to rank, sentence-transformers, FAISS, Pinecone, Weaviate, "
    "hybrid search, BM25, NDCG, MRR, evaluation, A/B testing. "
    "Strong NLP and machine learning foundations including fine-tuning LLMs, RAG, "
    "retrieval augmented generation, PyTorch, transformers, recommendation systems. "
    "5-9 years experience, product company background preferred, "
    "hands-on coding, end-to-end ML system deployment in production. "
    "Located in Pune or Noida preferred, Tier-1 Indian cities welcome."
)


def semantic_rerank(
    candidates: list[tuple[float, str, dict, dict]],
    blend_weight: float = 0.15,
) -> list[tuple[float, str, dict, dict]]:
    """
    Semantic re-ranking using sentence-transformers (all-MiniLM-L6-v2).

    Runs ONLY on the pre-filtered top candidates from the deterministic
    engine. Computes cosine similarity between JD embedding and each
    candidate's text profile, then blends:
        final_score = (1 - blend_weight) * det_score + blend_weight * sem_score

    Args:
        candidates: List of (score, cid, features, components) tuples
        blend_weight: Weight for semantic score (default 0.15)

    Returns:
        Re-ranked list with semantic_score added to components
    """
    try:
        from sentence_transformers import SentenceTransformer
        from sentence_transformers.util import cos_sim
    except ImportError:
        log.warning(
            "sentence-transformers not installed. "
            "Skipping semantic re-ranking. Install with: "
            "pip install sentence-transformers"
        )
        # Add placeholder semantic_score
        for i, (score, cid, feats, comps) in enumerate(candidates):
            comps["semantic_score"] = 0.0
        return candidates

    log.info("  Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Build text profiles
    texts = [_build_candidate_text(feats) for _, _, feats, _ in candidates]

    log.info(f"  Encoding {len(texts)} candidate profiles...")
    candidate_embeddings = model.encode(texts, show_progress_bar=False, batch_size=64)
    jd_embedding = model.encode([JD_TEXT], show_progress_bar=False)

    # Compute cosine similarities
    similarities = cos_sim(jd_embedding, candidate_embeddings)[0].tolist()

    # Normalize similarities to [0, 1] range
    sim_min = min(similarities)
    sim_max = max(similarities)
    sim_range = sim_max - sim_min if sim_max > sim_min else 1.0

    reranked = []
    for i, (det_score, cid, feats, comps) in enumerate(candidates):
        sem_score = (similarities[i] - sim_min) / sim_range
        comps["semantic_score"] = round(sem_score, 4)
        blended = (1 - blend_weight) * det_score + blend_weight * sem_score
        reranked.append((round(blended, 4), cid, feats, comps))

    # Re-sort by blended score
    reranked.sort(key=lambda x: (-x[0], x[1]))
    log.info("  Semantic re-ranking complete.")
    return reranked


# ---------------------------------------------------------------------------
# Cross-Encoder Deep Alignment Layer (Optional)
# ---------------------------------------------------------------------------

def cross_encoder_rerank(
    candidates: list[tuple[float, str, dict, dict]],
    blend_weight: float = 0.20,
) -> list[tuple[float, str, dict, dict]]:
    """
    Deep semantic re-ranking using a Cross-Encoder with sliding window
    max-pooling to handle long candidate profiles.

    The cross-encoder/ms-marco-MiniLM-L-6-v2 model has a 512-token context
    window. Dense professional histories often exceed this, causing critical
    data loss via truncation. This implementation:

    1. Tokenizes the candidate text
    2. If tokens <= 400: scores directly (fast path)
    3. If tokens > 400: segments into overlapping windows of 350 tokens
       with a step of 100, scores each window independently, then
       applies max-pooling: Score_final = max(s_1, s_2, ..., s_n)

    This preserves specialized experience hidden deep in long resumes.

    Uses: cross-encoder/ms-marco-MiniLM-L-6-v2
    Applied: ONLY to top 200 candidates from deterministic filtering.

    Args:
        candidates: List of (score, cid, features, components) tuples
        blend_weight: Weight for cross-encoder score (default 0.20)

    Returns:
        Re-ranked list with cross_encoder_score added to components
    """
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        log.warning(
            "sentence-transformers not installed or CrossEncoder unavailable. "
            "Skipping cross-encoder re-ranking."
        )
        for _, _, _, comps in candidates:
            comps["cross_encoder_score"] = 0.0
        return candidates

    log.info("  Loading Cross-Encoder model (ms-marco-MiniLM-L-6-v2)...")
    try:
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
    except Exception as e:
        log.warning(f"  Failed to load Cross-Encoder: {e}. Skipping.")
        for _, _, _, comps in candidates:
            comps["cross_encoder_score"] = 0.0
        return candidates

    # ── Sliding window parameters ─────────────────────────────────────
    WINDOW_SIZE = 350       # tokens per window
    STEP_SIZE = 100         # overlap step
    SHORT_THRESHOLD = 400   # below this, no windowing needed

    def _rough_tokenize(text: str) -> list[str]:
        """Fast whitespace tokenizer (close enough for length estimation)."""
        return text.split()

    def _score_candidate(jd: str, candidate_text: str) -> float:
        """
        Score a single candidate against the JD using sliding window
        max-pooling if the text exceeds the context window.
        """
        tokens = _rough_tokenize(candidate_text)

        if len(tokens) <= SHORT_THRESHOLD:
            # Fast path: fits in context window, score directly
            raw = model.predict([(jd, candidate_text)], show_progress_bar=False)
            return float(raw[0])

        # Sliding window: segment long text into overlapping chunks
        windows = []
        start = 0
        while start < len(tokens):
            end = min(start + WINDOW_SIZE, len(tokens))
            window_text = " ".join(tokens[start:end])
            windows.append(window_text)
            if end >= len(tokens):
                break
            start += STEP_SIZE

        # Score each window independently
        pairs = [(jd, w) for w in windows]
        window_scores = model.predict(pairs, show_progress_bar=False)

        # Max-pooling: take the highest window score
        return float(max(window_scores))

    # ── Score all candidates ──────────────────────────────────────────
    log.info(f"  Scoring {len(candidates)} candidates with sliding-window Cross-Encoder...")

    raw_scores = []
    for idx, (_, _, feats, _) in enumerate(candidates):
        candidate_text = _build_candidate_text(feats)
        score = _score_candidate(JD_TEXT, candidate_text)
        raw_scores.append(score)

        if (idx + 1) % 50 == 0:
            log.info(f"    Cross-Encoder progress: {idx + 1}/{len(candidates)}")

    # Apply sigmoid normalization to convert logits to [0, 1]
    import math as _math
    sigmoid_scores = [1.0 / (1.0 + _math.exp(-s)) for s in raw_scores]

    # Normalize to [0, 1] range within the cohort
    s_min = min(sigmoid_scores)
    s_max = max(sigmoid_scores)
    s_range = s_max - s_min if s_max > s_min else 1.0

    reranked = []
    for i, (det_score, cid, feats, comps) in enumerate(candidates):
        ce_score = (sigmoid_scores[i] - s_min) / s_range
        comps["cross_encoder_score"] = round(ce_score, 4)
        blended = (1 - blend_weight) * det_score + blend_weight * ce_score
        reranked.append((round(blended, 4), cid, feats, comps))

    reranked.sort(key=lambda x: (-x[0], x[1]))
    log.info("  Cross-Encoder re-ranking complete (sliding window + max-pooling).")
    return reranked


# ---------------------------------------------------------------------------
# Details JSON Export (powers the recruiter explanation UI)
# ---------------------------------------------------------------------------

def _generate_strengths_concerns(
    features: dict[str, Any],
    components: dict[str, float],
) -> tuple[list[str], list[str]]:
    """
    Generate structured strengths and concerns lists for the UI.
    Returns (strengths, concerns) as lists of human-readable strings.
    """
    raw_profile = features.get("raw_profile", {})
    title = raw_profile.get("current_title", "Unknown")
    years = features["years_exp"]
    location = raw_profile.get("location", "Unknown")
    rr = features["response_rate"]
    notice = features["notice_days"]

    strengths: list[str] = []
    concerns: list[str] = []

    # Title/career
    if components["title_career"] >= 0.7:
        strengths.append(f"{title} strongly aligns with Senior AI Engineer role")
    elif components["title_career"] >= 0.4:
        strengths.append(f"Relevant career trajectory as {title}")
    else:
        concerns.append(f"Current {title} role has limited AI engineering alignment")

    # Skills
    matched_skills = []
    for skill in features.get("skill_details", []):
        name = skill["name"]
        if name in SKILLS_CRITICAL:
            matched_skills.append(name.title())
        elif name in SKILLS_IMPORTANT:
            matched_skills.append(name.title())
    if len(matched_skills) >= 3:
        strengths.append(f"Strong skill coverage: {', '.join(matched_skills[:4])}")
    elif matched_skills:
        strengths.append(f"Relevant skills: {', '.join(matched_skills[:3])}")
    if components["skills"] < 0.2:
        concerns.append("Limited matching AI/ML skill set")

    # Experience
    if 5.0 <= years <= 9.0:
        strengths.append(f"{years:.0f}y experience fits the 5-9 year JD range")
    elif years < 3.0:
        concerns.append(f"Only {years:.1f}y experience (JD requires 5-9y)")
    elif years > 12:
        concerns.append(f"{years:.0f}y may indicate management shift; JD values hands-on coding")

    # Behavioral
    if rr >= 0.6:
        strengths.append(f"High platform engagement ({rr:.0%} response rate)")
    elif rr < 0.1:
        concerns.append(f"Very low response rate ({rr:.0%})")

    if notice > 90:
        concerns.append(f"{notice}-day notice period exceeds preferred range")
    elif notice <= 30:
        strengths.append("Available within 30-day notice window")

    # Location
    city = location.split(",")[0].strip() if location else ""
    if components["location"] >= 0.85:
        strengths.append(f"Located in preferred city: {city}")
    elif components["location"] < 0.4:
        concerns.append(f"Based in {location}; relocation uncertain")

    # Career quality
    if components["career_quality"] >= 0.8:
        strengths.append("Strong product engineering background")
    elif components["career_quality"] < 0.3:
        concerns.append("Limited product engineering or end-to-end ownership experience")

    # Education
    if components["education"] >= 0.85:
        strengths.append("Tier-1 institution with relevant field of study")

    return strengths[:5], concerns[:3]


def export_details_json(
    top_candidates: list[tuple[float, str, dict, dict]],
    output_path: str,
) -> None:
    """
    Export detailed per-candidate scoring data as JSON for the UI.
    Written alongside the CSV as submission_details.json.
    """
    details_path = str(Path(output_path).with_name("submission_details.json"))
    records = []

    for rank_idx, (score, cid, features, components) in enumerate(top_candidates):
        rank = rank_idx + 1
        raw_profile = features.get("raw_profile", {})
        strengths, concerns = _generate_strengths_concerns(features, components)

        records.append({
            "candidate_id": cid,
            "rank": rank,
            "score": round(score, 4),
            "components": {
                "title_career": round(components.get("title_career", 0), 4),
                "skills": round(components.get("skills", 0), 4),
                "experience": round(components.get("experience", 0), 4),
                "behavioral": round(components.get("behavioral", 0), 4),
                "location": round(components.get("location", 0), 4),
                "education": round(components.get("education", 0), 4),
                "career_quality": round(components.get("career_quality", 0), 4),
                "semantic_score": round(components.get("semantic_score", 0), 4),
            },
            "is_honeypot": components.get("is_honeypot", 0) > 0,
            "strengths": strengths,
            "concerns": concerns,
            "current_title": raw_profile.get("current_title", "Unknown"),
            "current_company": raw_profile.get("current_company", "Unknown"),
            "years_exp": features["years_exp"],
            "location": raw_profile.get("location", "Unknown"),
            "skill_names": features.get("skill_names", [])[:15],
            "response_rate": features["response_rate"],
            "notice_days": features["notice_days"],
        })

    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    log.info(f"  Details JSON written: {details_path} ({len(records)} records)")


def run_pipeline(
    candidates_path: str,
    output_path: str,
    use_semantic: bool = False,
    use_cross_encoder: bool = False,
    weight_schema: dict[str, float] | None = None,
) -> None:
    """
    Main ranking pipeline. Streams candidates, scores them, optionally
    applies semantic/cross-encoder re-ranking, selects top 100, and writes
    submission CSV + details JSON.

    Args:
        candidates_path: Path to .jsonl or .jsonl.gz candidates file.
        output_path: Path for the output submission CSV.
        use_semantic: Enable bi-encoder semantic re-ranking on top 500.
        use_cross_encoder: Enable cross-encoder deep alignment on top 200.
        weight_schema: Optional dynamic weight distribution from LLM.
    """
    start_time = time.time()
    today = date.today()

    log.info("=" * 65)
    log.info("Aethelgard — Hybrid Intelligence Engine V4 PRO")
    log.info("=" * 65)
    log.info(f"Candidates file: {candidates_path}")
    log.info(f"Output file:     {output_path}")
    log.info(f"Reference date:  {today}")
    if weight_schema:
        log.info(f"Dynamic weights: {weight_schema}")
    else:
        log.info("Weights: default (hardcoded)")
    log.info("")

    # ── Phase 1: Stream-process all candidates ────────────────────────
    # Use a min-heap of size 100 to maintain top candidates without
    # storing all 100K scored records in memory.
    # heapq is a min-heap, so we push (score, candidate_id, ...) and
    # the smallest scores get evicted naturally.
    TOP_N: int = 100
    HEAP_BUFFER: int = 500  # Keep more than 100 to handle tie-breaking
    heap: list[tuple[float, str, dict, dict]] = []

    candidates_processed: int = 0
    honeypots_found: int = 0
    parse_errors: int = 0

    log.info("Phase 1: Streaming candidate evaluation...")

    with open_candidates_file(candidates_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            # ── Parse candidate JSON ──────────────────────────────────
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError as e:
                parse_errors += 1
                if parse_errors <= 5:
                    log.warning(f"Line {line_num}: JSON parse error: {e}")
                continue

            # ── Extract features ──────────────────────────────────────
            features = extract_features(candidate, today)

            # ── Compute composite score ───────────────────────────────
            score, components = compute_composite_score(features, weight_schema=weight_schema)

            # Track honeypots
            if components.get("is_honeypot", 0.0) > 0:
                honeypots_found += 1

            candidates_processed += 1

            # ── Maintain top-N heap ───────────────────────────────────
            # Push to heap; if heap exceeds buffer size, trim to keep
            # only the top candidates
            candidate_id = features["candidate_id"]
            heapq.heappush(heap, (score, candidate_id, features, components))

            if len(heap) > HEAP_BUFFER:
                # Trim to keep top HEAP_BUFFER/2 candidates
                heap = heapq.nlargest(HEAP_BUFFER // 2, heap)
                heapq.heapify(heap)

            # Progress logging every 10K candidates
            if candidates_processed % 10000 == 0:
                elapsed = time.time() - start_time
                rate = candidates_processed / elapsed
                log.info(
                    f"  Processed {candidates_processed:>7,d} candidates "
                    f"({elapsed:.1f}s, {rate:.0f}/s)"
                )

    elapsed_phase1 = time.time() - start_time
    log.info(f"Phase 1 complete: {candidates_processed:,d} candidates in {elapsed_phase1:.1f}s")
    log.info(f"  Honeypots detected: {honeypots_found}")
    log.info(f"  Parse errors: {parse_errors}")
    log.info("")

    # ── Phase 2: Sort and select top 100 ──────────────────────────────
    log.info("Phase 2: Selecting top 100 candidates...")

    # Round scores to 4 decimal places BEFORE sorting so that
    # tie-breaking by candidate_id matches the rounded values in the CSV.
    all_scored = [
        (round(score, 4), cid, feats, comps)
        for score, cid, feats, comps in heap
    ]
    all_scored.sort(key=lambda x: (-x[0], x[1]))

    # Take top 100
    top_100 = all_scored[:TOP_N]

    if len(top_100) < TOP_N:
        log.error(
            f"Only {len(top_100)} candidates available; "
            f"need exactly {TOP_N}. Check input data."
        )
        sys.exit(1)

    log.info(f"  Top score:    {top_100[0][0]:.4f} ({top_100[0][1]})")
    log.info(f"  100th score:  {top_100[-1][0]:.4f} ({top_100[-1][1]})")
    log.info("")

    # ── Phase 2b: Semantic re-ranking (optional) ──────────────────────
    if use_semantic:
        log.info("Phase 2b: Semantic re-ranking on top 500...")
        top_for_semantic = all_scored[:500]
        top_for_semantic = semantic_rerank(top_for_semantic, blend_weight=0.15)
        top_100 = top_for_semantic[:TOP_N]
        log.info(f"  Blended top score:    {top_100[0][0]:.4f} ({top_100[0][1]})")
        log.info(f"  Blended 100th score:  {top_100[-1][0]:.4f} ({top_100[-1][1]})")
        log.info("")
    else:
        # Add placeholder semantic_score
        for _, _, _, comps in all_scored:
            comps["semantic_score"] = 0.0

    # ── Phase 2c: Cross-Encoder deep alignment (optional) ─────────────
    if use_cross_encoder:
        log.info("Phase 2c: Cross-Encoder deep alignment on top 200...")
        top_for_ce = all_scored[:200]
        top_for_ce = cross_encoder_rerank(top_for_ce, blend_weight=0.20)
        top_100 = top_for_ce[:TOP_N]
        log.info(f"  CE-blended top score:    {top_100[0][0]:.4f} ({top_100[0][1]})")
        log.info(f"  CE-blended 100th score:  {top_100[-1][0]:.4f} ({top_100[-1][1]})")
        log.info("")
    else:
        for _, _, _, comps in all_scored:
            comps.setdefault("cross_encoder_score", 0.0)

    # ── Phase 3: Generate reasoning and write CSV ─────────────────────
    log.info("Phase 3: Generating reasoning and writing CSV...")

    output_dir = Path(output_path).parent
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank_idx, (score, candidate_id, features, components) in enumerate(top_100):
            rank = rank_idx + 1  # 1-indexed
            reasoning = generate_reasoning(features, score, rank, components)

            # Round score to 4 decimal places for clean output
            writer.writerow([
                candidate_id,
                rank,
                f"{score:.4f}",
                reasoning,
            ])

    elapsed_total = time.time() - start_time
    log.info(f"Phase 3 complete.")

    # ── Export details JSON for the recruiter UI ──────────────────────
    export_details_json(top_100, output_path)

    log.info("")
    log.info("=" * 65)
    log.info(f"Pipeline complete in {elapsed_total:.1f}s")
    log.info(f"  Output: {output_path}")
    log.info(f"  Rows:   {TOP_N}")
    log.info(f"  Candidates evaluated: {candidates_processed:,d}")
    log.info(f"  Honeypots excluded:   {honeypots_found}")
    log.info("=" * 65)

    # ── Sanity check: validate output ─────────────────────────────────
    _validate_output(output_path)


def _validate_output(csv_path: str) -> None:
    """Quick self-validation of the output CSV."""
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 100, f"Expected 100 rows, got {len(rows)}"

    ranks = [int(r["rank"]) for r in rows]
    assert sorted(ranks) == list(range(1, 101)), "Ranks must be 1-100"

    scores = [float(r["score"]) for r in rows]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], (
            f"Scores not non-increasing: rank {i+1} ({scores[i]}) < "
            f"rank {i+2} ({scores[i+1]})"
        )

    ids = [r["candidate_id"] for r in rows]
    assert len(set(ids)) == 100, "Duplicate candidate IDs found"

    # Check tied scores have candidate_id ascending
    for i in range(len(scores) - 1):
        if scores[i] == scores[i + 1]:
            assert ids[i] < ids[i + 1], (
                f"Tied scores at ranks {i+1}/{i+2} must have "
                f"candidate_id ascending: {ids[i]} vs {ids[i+1]}"
            )

    log.info("Self-validation PASSED ✓")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="rank.py",
        description=(
            "Aethelgard — Deterministic Hiring Intelligence Engine. "
            "Ranks candidates against a Senior AI Engineer JD using a "
            "multi-signal weighted scoring pipeline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv\n"
            "  python rank.py --candidates ./candidates.jsonl --out ./output/team_aethelgard.csv\n"
        ),
    )
    parser.add_argument(
        "--candidates",
        type=str,
        required=True,
        help="Path to candidates file (.jsonl or .jsonl.gz)",
    )
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="Output path for submission CSV",
    )
    parser.add_argument(
        "--semantic",
        action="store_true",
        default=False,
        help="Enable semantic re-ranking on top 500 candidates (requires sentence-transformers)",
    )
    parser.add_argument(
        "--cross-encoder",
        action="store_true",
        default=False,
        dest="cross_encoder",
        help="Enable cross-encoder deep alignment on top 200 candidates",
    )
    parser.add_argument(
        "--weights-json",
        type=str,
        default=None,
        dest="weights_json",
        help="Path to JSON file with dynamic weight schema (from LLM)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # ── Validate inputs ───────────────────────────────────────────────
    candidates_path = Path(args.candidates)
    if not candidates_path.exists():
        log.error(f"Candidates file not found: {candidates_path}")
        sys.exit(1)

    if not (
        str(candidates_path).endswith(".jsonl")
        or str(candidates_path).endswith(".jsonl.gz")
        or str(candidates_path).endswith(".json")
    ):
        log.warning(
            f"Unexpected file extension: {candidates_path.suffix}. "
            f"Expected .jsonl, .jsonl.gz, or .json"
        )

    # ── Load dynamic weights if provided ───────────────────────────────
    weight_schema = None
    if args.weights_json:
        weights_path = Path(args.weights_json)
        if weights_path.exists():
            with open(weights_path, "r", encoding="utf-8") as wf:
                weight_schema = json.load(wf)
            log.info(f"Loaded dynamic weights from {weights_path}")
        else:
            log.warning(f"Weights file not found: {weights_path}. Using defaults.")

    # ── Run pipeline ──────────────────────────────────────────────────
    try:
        run_pipeline(
            str(candidates_path),
            args.out,
            use_semantic=args.semantic,
            use_cross_encoder=args.cross_encoder,
            weight_schema=weight_schema,
        )
    except KeyboardInterrupt:
        log.info("\nInterrupted by user.")
        sys.exit(130)
    except Exception as e:
        log.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
