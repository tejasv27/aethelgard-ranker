# Aethelgard — Deterministic Hiring Intelligence Engine

> A production-ready, CPU-only candidate ranking pipeline for the Redrob AI Hackathon.  
> Ranks 100,000 candidates against a Senior AI Engineer job description in under 5 minutes.

---

## Quick Start

```bash
# 1. Install dependencies (only PyYAML — ranking uses stdlib only)
pip install -r requirements.txt

# 2. Run the ranking pipeline
python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv

# 3. Validate the output
python validate_submission.py submission.csv
```

**That's it.** One command produces the submission CSV.

---

## Architecture Overview

```
candidates.jsonl.gz
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 1: Stream Processing                                  │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────┐ │
│  │ gzip.open()  │──▶│ JSON parse   │──▶│ Feature Extract   │ │
│  │ line-by-line │   │ per-line     │   │ 7 components      │ │
│  └─────────────┘   └──────────────┘   └───────┬───────────┘ │
│                                                │             │
│  ┌──────────────────────────────────────────────▼──────────┐ │
│  │ Honeypot Detection → Composite Score → Min-Heap (top N) │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 2: Sort & Select Top 100                              │
│  Sort by (score DESC, candidate_id ASC for ties)             │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 3: Reasoning Generation & CSV Output                  │
│  1-2 sentence explainable reasoning per candidate            │
│  Self-validation of output format                            │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
   submission.csv
```

---

## Deterministic Scoring Logic

The engine computes a composite score for each candidate as a **weighted sum of 7 components**:

| Component | Weight | What it measures |
|-----------|--------|------------------|
| **Title & Career** | 0.28 | Current title alignment + career trajectory toward AI/ML roles |
| **Skills** | 0.22 | Skill match quality with trust multiplier (endorsements × duration × proficiency) |
| **Experience** | 0.15 | Years of experience fit against the 5-9 year range (shaped curve, not threshold) |
| **Behavioral** | 0.15 | Availability float: response rate × notice period × recency × open-to-work |
| **Location** | 0.08 | Tier-1 Indian city match, Pune/Noida preference, relocation willingness |
| **Career Quality** | 0.07 | Product company vs. services/consulting firm career history |
| **Education** | 0.05 | Institution tier + relevant field of study |

### Why these weights?

The JD makes several things very clear:

1. **Title alignment matters most** — The JD explicitly says "The right answer is NOT find candidates whose skills section contains the most AI keywords." A Marketing Manager with AI keywords is not a fit. A Senior ML Engineer with fewer listed skills probably is.

2. **Skill quality > skill quantity** — We apply a trust multiplier: `proficiency × duration_months × endorsements`. A skill with "expert" proficiency but 0 months duration and 0 endorsements is suspicious (and a honeypot signal).

3. **Behavioral signals are critical** — The JD says to down-weight candidates who haven't logged in for 6 months or have a 5% response rate.

4. **Career trajectory** — The JD penalizes all-services-firm careers (TCS, Infosys, Wipro, etc.) unless there's product company experience too.

---

## Honeypot Detection

The engine detects ~80 honeypot candidates using these rules:

| Check | Threshold | Penalty |
|-------|-----------|---------|
| Skills count vs experience | >15 skills AND <2 years exp | Score × 0.01 |
| Near-zero response rate | Response rate ≤ 0.02 | Score × 0.01 |
| Expert skills with no duration | ≥5 expert skills with <3 months | Score × 0.01 |
| Skill stuffing | >20 skills AND <4 years exp | Score × 0.01 |
| Zero-endorsement experts | ≥8 adv/expert skills with 0 endorsements, <6 months | Score × 0.01 |
| Impossible career timeline | Career months > 2× stated experience | Score × 0.01 |

Any candidate triggering a penalty score ≥50 is flagged as a honeypot and their composite score is crushed to near-zero.

---

## Title Disqualification Logic

The JD is explicit about roles that **don't** fit:

- **Tier 1 (Score 1.0)**: AI Engineer, ML Engineer, Applied Scientist, NLP Engineer, Ranking Engineer, Search Engineer
- **Tier 2 (Score 0.65)**: Data Scientist, Software Engineer, Tech Lead, Data Engineer
- **Tier 3 (Score 0.25)**: Product Manager, DevOps, Solutions Architect
- **Disqualified (Score 0.0 + penalty)**: Marketing Manager, HR Manager, Sales Executive, Accountant, Graphic Designer, Civil Engineer, Mechanical Engineer

---

## Performance

| Metric | Value |
|--------|-------|
| Runtime (100K candidates) | ~60 seconds |
| Peak memory | ~1.5 GB |
| CPU cores used | 1 (single-threaded) |
| External dependencies | 0 (stdlib only) |
| Network calls | 0 |
| GPU required | No |

The pipeline is well within the hackathon's 5-minute / 16GB / CPU-only constraints.

---

## File Structure

```
aethelgard_hackathon/
├── rank.py                        # Main ranking engine (single command)
├── requirements.txt               # Minimal deps (PyYAML only)
├── submission_metadata.yaml       # Hackathon metadata template
├── README.md                      # This file
├── docs/
│   └── india_runs_challenge.md    # Full challenge specification
└── submission.csv                 # Generated output (after running)
```

---

## Reproduce Command

```bash
python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv
```

Supports both `.jsonl.gz` (gzipped) and `.jsonl` (plain) input formats.

---

## Design Decisions & Trade-offs

### Why not embeddings/vector search?

The 5-minute CPU budget for 100K candidates makes vector embeddings infeasible:
- Loading a sentence-transformer model: ~30 seconds
- Encoding 100K candidate texts: ~10-15 minutes on CPU
- Even with pre-computed embeddings, the JD requires real-time ranking

Our deterministic rule-based approach runs in ~60 seconds and produces **explainable** scores.

### Why title alignment is weighted highest?

The JD's "Final note for hackathon participants" explicitly warns against keyword matching. The sample submission (provided as a format reference) ranks HR Managers and Accountants in the top 10 — this is intentionally bad. Title + career trajectory is the single strongest signal against this trap.

### Why a trust multiplier on skills?

Skills with `proficiency: "expert"` but `duration_months: 0` and `endorsements: 0` are a honeypot signal. Real experts have endorsements and years of usage. The trust multiplier naturally down-weights suspicious skill claims.

### Why streaming with a min-heap?

Processing 100K JSONL records doesn't require loading everything into memory. Streaming line-by-line with a bounded heap keeps peak memory under 2GB even for large datasets.

---

## Validation

After running, validate your output:

```bash
python validate_submission.py submission.csv
```

The engine also performs self-validation after writing, checking:
- Exactly 100 rows
- Ranks 1-100 each used exactly once
- Scores non-increasing with rank
- Tied scores have candidate_id ascending
- No duplicate candidate IDs

---

## License

MIT
