# API Reference

## ai_core.py
`generate_dynamic_weights(jd_text: str) -> tuple[dict, str]`
Invokes Gemini 2.5 Flash to analyze the provided JD text and return normalized 7-axis scoring weights via strict Pydantic schemas.

## database.py
`AethelgardDB`
- `record_feedback(candidate_id, feedback_type, adjustment)`: UPSERTs recruiter feedback to SQLite.
- `cache_job_profile(jd_text, weights, source)`: Caches dynamic weights generated for a specific JD.
- `log_pipeline_run(details)`: Logs pipeline execution to the compliance audit table.

## rank.py
`cross_encoder_rerank(candidates, blend_weight)`
Applies sliding-window Cross-Encoder semantic matching to the candidate list.
