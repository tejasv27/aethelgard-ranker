#!/usr/bin/env python3
"""Quick smoke test for the Aethelgard scoring engine."""

import sys
sys.path.insert(0, ".")
from rank import extract_features, compute_composite_score, detect_honeypot, generate_reasoning
from datetime import date

today = date(2026, 6, 10)

# --- Test 1: Strong AI candidate ---
good_candidate = {
    "candidate_id": "CAND_0000100",
    "profile": {
        "anonymized_name": "Test Good",
        "headline": "Senior ML Engineer | Embeddings, RAG, Vector Search",
        "summary": "ML engineer with 7 years building embeddings and retrieval systems at product companies.",
        "location": "Pune, Maharashtra",
        "country": "India",
        "years_of_experience": 7.0,
        "current_title": "Senior Machine Learning Engineer",
        "current_company": "StartupXYZ",
        "current_company_size": "51-200",
        "current_industry": "Technology"
    },
    "career_history": [
        {"company": "StartupXYZ", "title": "Senior Machine Learning Engineer", "start_date": "2022-01-01", "end_date": None, "duration_months": 53, "is_current": True, "industry": "Technology", "company_size": "51-200", "description": "Built production ranking and retrieval systems using embeddings and vector search. Deployed ML models end-to-end."},
        {"company": "ProductCo", "title": "ML Engineer", "start_date": "2019-01-01", "end_date": "2021-12-31", "duration_months": 36, "is_current": False, "industry": "Technology", "company_size": "201-500", "description": "Developed NLP pipelines and recommendation systems for real users at scale."}
    ],
    "education": [{"institution": "IIT Delhi", "degree": "M.Tech", "field_of_study": "Computer Science", "start_year": 2015, "end_year": 2017, "grade": "9.1 CGPA", "tier": "tier_1"}],
    "skills": [
        {"name": "embeddings", "proficiency": "expert", "endorsements": 25, "duration_months": 48},
        {"name": "retrieval", "proficiency": "advanced", "endorsements": 18, "duration_months": 36},
        {"name": "ranking", "proficiency": "advanced", "endorsements": 15, "duration_months": 30},
        {"name": "python", "proficiency": "expert", "endorsements": 40, "duration_months": 84},
        {"name": "faiss", "proficiency": "advanced", "endorsements": 12, "duration_months": 24},
        {"name": "nlp", "proficiency": "advanced", "endorsements": 20, "duration_months": 48},
        {"name": "pytorch", "proficiency": "advanced", "endorsements": 15, "duration_months": 36},
    ],
    "certifications": [],
    "languages": [{"language": "English", "proficiency": "professional"}],
    "redrob_signals": {
        "profile_completeness_score": 92, "signup_date": "2025-06-01", "last_active_date": "2026-06-05",
        "open_to_work_flag": True, "profile_views_received_30d": 45, "applications_submitted_30d": 3,
        "recruiter_response_rate": 0.85, "avg_response_time_hours": 12, "skill_assessment_scores": {"embeddings": 88},
        "connection_count": 500, "endorsements_received": 120, "notice_period_days": 30,
        "expected_salary_range_inr_lpa": {"min": 30, "max": 45}, "preferred_work_mode": "hybrid",
        "willing_to_relocate": True, "github_activity_score": 72, "search_appearance_30d": 300,
        "saved_by_recruiters_30d": 12, "interview_completion_rate": 0.95, "offer_acceptance_rate": 0.8,
        "verified_email": True, "verified_phone": True, "linkedin_connected": True
    }
}

# --- Test 2: Honeypot candidate ---
honeypot = {
    "candidate_id": "CAND_0099999",
    "profile": {
        "anonymized_name": "Test Honeypot",
        "headline": "AI Expert",
        "summary": "Expert in everything AI.",
        "location": "Mumbai",
        "country": "India",
        "years_of_experience": 1.5,
        "current_title": "AI Engineer",
        "current_company": "FakeCo",
        "current_company_size": "1-10",
        "current_industry": "Technology"
    },
    "career_history": [{"company": "FakeCo", "title": "AI Engineer", "start_date": "2025-01-01", "end_date": None, "duration_months": 17, "is_current": True, "industry": "Technology", "company_size": "1-10", "description": "AI work."}],
    "education": [{"institution": "Unknown", "degree": "B.E.", "field_of_study": "CS", "start_year": 2022, "end_year": 2024, "grade": "7.0", "tier": "tier_4"}],
    "skills": [{"name": "skill_%d" % i, "proficiency": "expert", "endorsements": 0, "duration_months": 0} for i in range(20)],
    "certifications": [],
    "languages": [],
    "redrob_signals": {
        "profile_completeness_score": 30, "signup_date": "2026-01-01", "last_active_date": "2026-01-15",
        "open_to_work_flag": True, "profile_views_received_30d": 0, "applications_submitted_30d": 0,
        "recruiter_response_rate": 0.01, "avg_response_time_hours": 500, "skill_assessment_scores": {},
        "connection_count": 2, "endorsements_received": 0, "notice_period_days": 0,
        "expected_salary_range_inr_lpa": {"min": 5, "max": 100}, "preferred_work_mode": "remote",
        "willing_to_relocate": False, "github_activity_score": -1, "search_appearance_30d": 0,
        "saved_by_recruiters_30d": 0, "interview_completion_rate": 0, "offer_acceptance_rate": -1,
        "verified_email": False, "verified_phone": False, "linkedin_connected": False
    }
}

# --- Test 3: Non-technical candidate (Marketing Manager) ---
bad_fit = {
    "candidate_id": "CAND_0050000",
    "profile": {
        "anonymized_name": "Test BadFit",
        "headline": "Marketing Manager | Brand Strategy",
        "summary": "Marketing professional with 8 years driving brand strategy.",
        "location": "Pune",
        "country": "India",
        "years_of_experience": 8.0,
        "current_title": "Marketing Manager",
        "current_company": "BrandCo",
        "current_company_size": "201-500",
        "current_industry": "Marketing"
    },
    "career_history": [{"company": "BrandCo", "title": "Marketing Manager", "start_date": "2020-01-01", "end_date": None, "duration_months": 77, "is_current": True, "industry": "Marketing", "company_size": "201-500", "description": "Led brand strategy and marketing campaigns."}],
    "education": [{"institution": "Mumbai Univ", "degree": "MBA", "field_of_study": "Marketing", "start_year": 2014, "end_year": 2016, "grade": "8.0", "tier": "tier_3"}],
    "skills": [
        {"name": "embeddings", "proficiency": "expert", "endorsements": 50, "duration_months": 60},
        {"name": "faiss", "proficiency": "expert", "endorsements": 40, "duration_months": 48},
        {"name": "qdrant", "proficiency": "expert", "endorsements": 35, "duration_months": 36},
        {"name": "python", "proficiency": "expert", "endorsements": 30, "duration_months": 84},
        {"name": "ranking", "proficiency": "advanced", "endorsements": 20, "duration_months": 24},
        {"name": "nlp", "proficiency": "advanced", "endorsements": 25, "duration_months": 48},
        {"name": "retrieval", "proficiency": "advanced", "endorsements": 15, "duration_months": 30},
        {"name": "marketing", "proficiency": "expert", "endorsements": 60, "duration_months": 96},
    ],
    "certifications": [],
    "languages": [{"language": "English", "proficiency": "native"}],
    "redrob_signals": {
        "profile_completeness_score": 85, "signup_date": "2025-01-01", "last_active_date": "2026-06-01",
        "open_to_work_flag": True, "profile_views_received_30d": 20, "applications_submitted_30d": 5,
        "recruiter_response_rate": 0.72, "avg_response_time_hours": 24, "skill_assessment_scores": {},
        "connection_count": 300, "endorsements_received": 80, "notice_period_days": 30,
        "expected_salary_range_inr_lpa": {"min": 20, "max": 35}, "preferred_work_mode": "hybrid",
        "willing_to_relocate": True, "github_activity_score": -1, "search_appearance_30d": 100,
        "saved_by_recruiters_30d": 5, "interview_completion_rate": 0.80, "offer_acceptance_rate": 0.5,
        "verified_email": True, "verified_phone": True, "linkedin_connected": True
    }
}

print("=" * 65)
print("Aethelgard Scoring Engine — Smoke Tests")
print("=" * 65)

# Test good candidate
f1 = extract_features(good_candidate, today)
s1, c1 = compute_composite_score(f1)
r1 = generate_reasoning(f1, s1, 1, c1)
print("\n--- Test 1: Strong AI Candidate ---")
print("  Score:        %.4f" % s1)
print("  Title/Career: %.3f" % c1["title_career"])
print("  Skills:       %.3f" % c1["skills"])
print("  Experience:   %.3f" % c1["experience"])
print("  Behavioral:   %.3f" % c1["behavioral"])
print("  Location:     %.3f" % c1["location"])
print("  Career Qual:  %.3f" % c1["career_quality"])
print("  Education:    %.3f" % c1["education"])
print("  Honeypot:     %.0f" % c1["is_honeypot"])
print("  Reasoning:    %s" % r1)
assert s1 > 0.6, "Good candidate should score >0.6, got %.4f" % s1
assert c1["is_honeypot"] == 0.0, "Good candidate should NOT be honeypot"
print("  PASS ✓")

# Test honeypot
f2 = extract_features(honeypot, today)
s2, c2 = compute_composite_score(f2)
hp, hp_reason = detect_honeypot(f2)
r2 = generate_reasoning(f2, s2, 100, c2)
print("\n--- Test 2: Honeypot Candidate ---")
print("  Score:        %.4f" % s2)
print("  Honeypot:     %s" % hp)
print("  HP Reason:    %s" % hp_reason)
print("  Reasoning:    %s" % r2)
assert hp is True, "Honeypot should be detected"
assert s2 < 0.05, "Honeypot should score <0.05, got %.4f" % s2
print("  PASS ✓")

# Test bad fit → non-technical role mismatch (Marketing Manager with AI keywords)
f3 = extract_features(bad_fit, today)
s3, c3 = compute_composite_score(f3)
r3 = generate_reasoning(f3, s3, 80, c3)
print("\n--- Test 3: Marketing Manager with AI Keywords ---")
print("  Score:        %.4f" % s3)
print("  Title/Career: %.3f" % c3["title_career"])
print("  Skills:       %.3f" % c3["skills"])
print("  Reasoning:    %s" % r3)
assert s3 < s1, "Marketing manager should score below AI engineer (%.4f vs %.4f)" % (s3, s1)
assert c3["title_career"] < 0.15, "Marketing manager title score should be low"
print("  PASS ✓")

# Verify ordering
print("\n--- Score ordering ---")
print("  Good AI Eng:     %.4f" % s1)
print("  Marketing Mgr:   %.4f" % s3)
print("  Honeypot:        %.4f" % s2)
assert s1 > s3 > s2, "Ordering should be: Good > BadFit > Honeypot"
print("  Ordering correct ✓")

print("\n" + "=" * 65)
print("ALL SMOKE TESTS PASSED ✓")
print("=" * 65)
