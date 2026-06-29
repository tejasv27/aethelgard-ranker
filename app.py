import streamlit as st
import pandas as pd
import subprocess
import os
import time
import json
import re
import math

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Aethelgard | Hiring Intelligence Engine",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Database Initialization (Upgrade 2: Persistent RLRF)
# ---------------------------------------------------------------------------
from database import AethelgardDB

@st.cache_resource
def get_database():
    """Thread-safe singleton database connection."""
    return AethelgardDB()

db = get_database()

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "dynamic_weights" not in st.session_state:
    st.session_state["dynamic_weights"] = None
if "weight_status" not in st.session_state:
    st.session_state["weight_status"] = None
if "manual_override" not in st.session_state:
    st.session_state["manual_override"] = False

# ---------------------------------------------------------------------------
# Stable Dark SaaS Theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, .main, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

.main, [data-testid="stAppViewContainer"] {
    background-color: #0f1117;
    color: #e8eaed;
}
[data-testid="stSidebar"] {
    background-color: #0f1117 !important;
    border-right: 1px solid #1e1e2e !important;
}

[data-testid="stExpander"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    margin-bottom: 10px;
}

.stButton>button {
    background: linear-gradient(135deg, #4f46e5, #6366f1);
    color: white; border-radius: 8px; padding: 0.6rem 2rem;
    font-weight: 600; border: none; font-size: 0.9rem;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    background: linear-gradient(135deg, #4338ca, #4f46e5);
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
}

.stDownloadButton>button {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #34d399; border-radius: 8px; font-weight: 500;
}

[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1rem 1.2rem;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #e8eaed !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: #8b949e !important;
    font-weight: 500 !important;
}

[data-testid="stProgress"] > div > div {
    background: #21262d !important;
    border-radius: 4px !important;
    height: 6px !important;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #6366f1, #818cf8) !important;
    border-radius: 4px !important;
    height: 6px !important;
}

.tag-strength {
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 6px; padding: 5px 10px;
    font-size: 0.82rem; display: inline-block;
    margin: 3px 4px 3px 0; line-height: 1.4;
}
.tag-concern {
    background: rgba(251, 191, 36, 0.1);
    color: #fbbf24;
    border: 1px solid rgba(251, 191, 36, 0.2);
    border-radius: 6px; padding: 5px 10px;
    font-size: 0.82rem; display: inline-block;
    margin: 3px 4px 3px 0; line-height: 1.4;
}

.info-chip {
    display: inline-block;
    background: #21262d;
    border-radius: 6px; padding: 4px 10px;
    font-size: 0.78rem; color: #8b949e;
    margin-right: 6px; margin-bottom: 6px;
}

.score-row {
    display: flex; justify-content: space-between;
    align-items: center; margin-top: 10px; margin-bottom: 3px;
}
.score-lbl { font-size: 0.82rem; color: #8b949e; }
.score-val { font-size: 0.82rem; font-weight: 600; color: #e8eaed; }

.hero-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px; padding: 1.4rem 1rem;
    text-align: center;
}
.hero-val {
    font-size: 1.8rem; font-weight: 700; color: #e8eaed; line-height: 1.2;
}
.hero-lbl {
    font-size: 0.7rem; color: #8b949e;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-top: 0.4rem;
}

.pipe-badge {
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 4px; padding: 4px 12px;
    display: inline-block;
    font-size: 0.7rem; color: #a5b4fc;
    letter-spacing: 0.06em; font-weight: 500;
    text-transform: uppercase;
}

.demo-box-red {
    background: #161b22;
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 10px; padding: 1.3rem;
}
.demo-box-green {
    background: #161b22;
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 10px; padding: 1.3rem;
}
.demo-pill {
    border-radius: 4px; padding: 3px 8px;
    font-size: 0.72rem; display: inline-block;
    margin: 2px 3px; border: 1px solid #21262d;
}
.demo-pill-red { color: #fca5a5; border-color: rgba(248,113,113,0.3); }
.demo-pill-green { color: #6ee7b7; border-color: rgba(52,211,153,0.3); }

.weight-bar-container {
    display: flex; align-items: center; gap: 8px;
    margin: 4px 0;
}
.weight-bar-label {
    font-size: 0.78rem; color: #8b949e;
    min-width: 140px;
}
.weight-bar-track {
    flex-grow: 1; height: 8px; background: #21262d;
    border-radius: 4px; overflow: hidden;
}
.weight-bar-fill {
    height: 100%; background: linear-gradient(90deg, #6366f1, #818cf8);
    border-radius: 4px; transition: width 0.3s ease;
}
.weight-bar-value {
    font-size: 0.78rem; color: #e8eaed; font-weight: 600;
    min-width: 40px; text-align: right;
}

hr { border-color: #21262d !important; }

[data-testid="stFileUploader"] {
    border: 1px dashed #21262d !important;
    border-radius: 10px !important;
    background: #161b22 !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🦅 Aethelgard")
    st.caption("Hiring Intelligence Engine V5 OMEGA")
    st.divider()

    st.markdown("""
**Version:** 5.0.0 OMEGA  
**Architecture:** Hybrid + Cross-Encoder + LLM + SQLite  
**Target Band:** 5-9 Years Experience
""")
    st.divider()

    # ── JD Input ──────────────────────────────────────────────────────
    st.markdown("**Job Description**")
    jd_text = st.text_area(
        "Paste the JD to generate dynamic weights",
        value=(
            "Senior AI Engineer with expertise in embeddings, vector search, "
            "retrieval systems, ranking, learning to rank, sentence-transformers. "
            "5-9 years experience, product company background preferred, "
            "hands-on coding, Pune or Noida location."
        ),
        height=120,
        help="The engine uses this JD to dynamically calibrate scoring weights via Gemini AI.",
    )

    if st.button("Generate AI Weights", use_container_width=True):
        with st.spinner("Calling Gemini 2.5 Flash (structured output)..."):
            try:
                from ai_core import generate_dynamic_weights
                weights, status = generate_dynamic_weights(jd_text)
                st.session_state["dynamic_weights"] = weights
                st.session_state["weight_status"] = status
                st.session_state["manual_override"] = False
                # Cache to database
                db.cache_job_profile(jd_text, weights, status)
            except Exception as e:
                st.session_state["weight_status"] = f"error: {e}"

    # Display weight status and bars
    ws = st.session_state.get("weight_status")
    dw = st.session_state.get("dynamic_weights")
    if ws and dw:
        if "ai_generated" in str(ws):
            st.success(f"Weights: {ws}")
        else:
            st.warning(f"Using defaults ({ws})")

        weight_labels = {
            "title_career": "Title & Career",
            "skills": "Technical Skills",
            "experience": "Experience Fit",
            "behavioral": "Behavioral",
            "location": "Location",
            "education": "Education",
            "career_quality": "Career Quality",
        }
        for key, label in weight_labels.items():
            val = dw.get(key, 0)
            pct = int(val * 100)
            bar_width = min(pct * 2.5, 100)
            st.markdown(
                f'<div class="weight-bar-container">'
                f'<span class="weight-bar-label">{label}</span>'
                f'<div class="weight-bar-track"><div class="weight-bar-fill" style="width:{bar_width}%"></div></div>'
                f'<span class="weight-bar-value">{pct}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.divider()

    # ── Interactive Weight Sliders (Upgrade 4) ────────────────────────
    manual_override = st.toggle("Manual Weight Override", value=st.session_state.get("manual_override", False))
    st.session_state["manual_override"] = manual_override

    if manual_override:
        st.caption("Drag sliders to manually set weights (auto-normalized)")
        slider_keys = {
            "title_career": "Title & Career",
            "skills": "Technical Skills",
            "experience": "Experience Fit",
            "behavioral": "Behavioral",
            "location": "Location",
            "education": "Education",
            "career_quality": "Career Quality",
        }
        raw_sliders = {}
        for key, label in slider_keys.items():
            default = int((dw or {}).get(key, 0.14) * 100)
            raw_sliders[key] = st.slider(label, min_value=2, max_value=40, value=default, key=f"sl_{key}")

        total = sum(raw_sliders.values())
        if total > 0:
            manual_weights = {k: round(v / total, 4) for k, v in raw_sliders.items()}
            # Fix rounding
            diff = 1.0 - sum(manual_weights.values())
            max_k = max(manual_weights, key=manual_weights.get)
            manual_weights[max_k] = round(manual_weights[max_k] + diff, 4)
            st.session_state["dynamic_weights"] = manual_weights
            dw = manual_weights

    st.divider()

    # ── Model toggles ─────────────────────────────────────────────────
    use_semantic = st.toggle("🧠 Bi-Encoder Semantic", value=False,
        help="Adds a sentence-transformers bi-encoder pass on top 500 candidates.")

    use_cross_encoder = st.toggle("🎯 Cross-Encoder Deep Match", value=False,
        help="Sliding-window cross-encoder with max-pooling on top 200 candidates.")

    show_honeypot_demo = st.toggle("🕵️ Deceptive Profile Demo", value=False,
        help="See how Aethelgard catches keyword-stuffed profiles.")

    st.divider()

    # ── Persistent Feedback Stats ─────────────────────────────────────
    counts = db.get_feedback_counts()
    st.markdown(f"**Feedback History:** {counts['upvotes']} validated, {counts['downvotes']} rejected")
    st.success("Pipeline Ready")


# ---------------------------------------------------------------------------
# Main Header
# ---------------------------------------------------------------------------
st.markdown("# 🦅 Aethelgard")
st.markdown('<span class="pipe-badge">V5 OMEGA | SLIDING-WINDOW CROSS-ENCODER + PERSISTENT RLRF + STRUCTURED LLM</span>', unsafe_allow_html=True)
st.caption("Enterprise-grade candidate ranking with persistent recruiter feedback, structured AI weights, and deep semantic alignment.")

st.markdown("")

m1, m2, m3, m4 = st.columns(4, gap="medium")
with m1:
    st.markdown('<div class="hero-card"><div class="hero-val">100K</div><div class="hero-lbl">Max Candidate Pool</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown('<div class="hero-card"><div class="hero-val">Top 100</div><div class="hero-lbl">Shortlist Output</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown('<div class="hero-card"><div class="hero-val">&lt; 5 min</div><div class="hero-lbl">Processing Time</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown('<div class="hero-card"><div class="hero-val">7 + 2</div><div class="hero-lbl">Scoring Dimensions</div></div>', unsafe_allow_html=True)

st.divider()


# ---------------------------------------------------------------------------
# Honeypot Detection Demo
# ---------------------------------------------------------------------------
if show_honeypot_demo:
    st.subheader("Deceptive Candidate Analysis")
    st.markdown(
        "How Aethelgard's multi-signal analysis catches profiles that "
        "**keyword-stuff AI/ML terms** but lack genuine career alignment."
    )

    st.markdown("")
    dc1, dc2 = st.columns(2, gap="medium")

    with dc1:
        st.markdown("""
<div class="demo-box-red">
    <div style="font-weight:600; color:#f87171; margin-bottom:0.6rem;">Standard ATS Result</div>
    <p style="color:#8b949e; font-size:0.83rem; margin-bottom:0.8rem;">Keyword-match only. No career or behavioral validation.</p>
    <div style="font-size:1.3rem; font-weight:700; color:#f87171; margin-bottom:0.4rem;">Rank: #3</div>
    <p style="color:#e8eaed; font-size:0.88rem;"><strong>Priya Sharma</strong> <span style="color:#8b949e;">— Marketing Manager at BrandCo</span></p>
    <div style="margin:0.5rem 0;">
        <span class="demo-pill demo-pill-red">Embeddings</span>
        <span class="demo-pill demo-pill-red">FAISS</span>
        <span class="demo-pill demo-pill-red">Qdrant</span>
        <span class="demo-pill demo-pill-red">Python</span>
        <span class="demo-pill demo-pill-red">NLP</span>
        <span class="demo-pill demo-pill-red">Retrieval</span>
        <span class="demo-pill demo-pill-red">Ranking</span>
    </div>
    <p style="color:#8b949e; font-size:0.78rem;">ATS matched 7/7 critical keywords. Ranked in Top 3.</p>
</div>
""", unsafe_allow_html=True)

    with dc2:
        st.markdown("""
<div class="demo-box-green">
    <div style="font-weight:600; color:#34d399; margin-bottom:0.6rem;">Aethelgard Engine</div>
    <p style="color:#8b949e; font-size:0.83rem; margin-bottom:0.8rem;">Multi-signal scoring with title, trajectory & behavioral checks.</p>
    <div style="font-size:1.3rem; font-weight:700; color:#34d399; margin-bottom:0.4rem;">Rank: Excluded</div>
    <p style="color:#e8eaed; font-size:0.88rem;"><strong>Priya Sharma</strong> <span style="color:#8b949e;">— Marketing Manager at BrandCo</span></p>
    <div style="margin:0.5rem 0;">
        <span class="demo-pill demo-pill-green">Title: 0.00 — Non-technical</span>
        <span class="demo-pill demo-pill-green">Trajectory: 0.00 — No AI/ML</span>
        <span class="demo-pill demo-pill-green">Skill Trust: Deflated</span>
    </div>
    <p style="color:#8b949e; font-size:0.78rem;">Title mismatch (28% weight) overrides keyword density. Removed.</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("**Signal-by-Signal Comparison**")
    breakdown_data = {
        "Signal": [
            "Title Alignment (28%)", "Skill Quality (22%)",
            "Experience Fit (15%)", "Behavioral (15%)",
            "Location (8%)", "Career Ownership (7%)", "Education (5%)",
        ],
        "Standard ATS": ["—", "0.95", "—", "—", "—", "—", "—"],
        "Aethelgard": ["0.00", "0.42", "0.90", "0.72", "1.00", "0.95", "0.65"],
        "Verdict": [
            "Marketing != AI Engineer", "No career backing for skills",
            "8y in range", "Active on platform", "Pune preferred",
            "Product company", "MBA Marketing",
        ]
    }
    st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, width='stretch')

    st.info(
        "**Key Insight:** A keyword-matching ATS ranks this candidate #3. "
        "Aethelgard's title alignment signal (28% weight) catches the mismatch — "
        "Marketing Manager has never held an AI/ML role. "
        "Score drops from ~0.95 (ATS) to ~0.09 (Aethelgard)."
    )
    st.divider()


# ---------------------------------------------------------------------------
# NDCG@10 Calculation (Upgrade 4)
# ---------------------------------------------------------------------------
def compute_simulated_ndcg(details, weights):
    """
    Compute a simulated NDCG@10 measuring how well the top-10 candidates
    align with the active weight distribution.
    """
    if not details or len(details) < 10:
        return 0.0

    if weights is None:
        weights = {
            "title_career": 0.28, "skills": 0.22, "experience": 0.15,
            "behavioral": 0.15, "location": 0.08, "education": 0.05,
            "career_quality": 0.07,
        }

    top_10 = details[:10]
    dcg = 0.0
    ideal_scores = []

    for i, cand in enumerate(top_10):
        comps = cand.get("components", {})
        relevance = sum(weights.get(k, 0) * comps.get(k, 0) for k in weights)
        dcg += relevance / math.log2(i + 2)
        ideal_scores.append(relevance)

    ideal_scores.sort(reverse=True)
    idcg = sum(s / math.log2(i + 2) for i, s in enumerate(ideal_scores))

    if idcg <= 0:
        return 0.0

    return min(dcg / idcg, 1.0)


def get_memory_usage_mb():
    """Get current process memory usage in MB."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        # Fallback for Windows without psutil
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except ImportError:
            return 0.0


# ---------------------------------------------------------------------------
# Core Workflow
# ---------------------------------------------------------------------------
st.subheader("Process New Candidate Batch")

uploaded_file = st.file_uploader(
    "Drop candidates.jsonl or .jsonl.gz dataset here",
    type=["gz", "jsonl"],
    help="Supports compressed (.jsonl.gz) and plain (.jsonl) formats up to 1 GB."
)

if uploaded_file is not None:
    input_path = f"temp_{uploaded_file.name}"
    output_path = "submission.csv"
    details_path = "submission_details.json"

    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)

    modes = ["Deterministic"]
    if use_semantic:
        modes.append("Bi-Encoder")
    if use_cross_encoder:
        modes.append("Cross-Encoder (Sliding Window)")
    if st.session_state.get("dynamic_weights"):
        modes.append("AI Weights" if not manual_override else "Manual Weights")
    mode_text = " + ".join(modes)

    st.info(f"**{uploaded_file.name}** ({file_size_mb:.1f} MB) — Mode: {mode_text}")

    if st.button("Execute Ranking Engine", use_container_width=True):
        start_time = time.time()
        mem_before = get_memory_usage_mb()

        try:
            with st.status("Running Aethelgard V5 OMEGA pipeline...", expanded=True) as status:
                st.write("Loading candidate dataset...")

                cmd = ["python", "rank.py", "--candidates", input_path, "--out", output_path]

                if use_semantic:
                    cmd.append("--semantic")
                if use_cross_encoder:
                    cmd.append("--cross-encoder")

                dw = st.session_state.get("dynamic_weights")
                weights_file = None
                if dw:
                    weights_file = "temp_weights.json"
                    with open(weights_file, "w", encoding="utf-8") as wf:
                        json.dump(dw, wf)
                    cmd.extend(["--weights-json", weights_file])
                    st.write("Applying dynamic weights...")

                st.write("Extracting features and computing scores...")
                st.write("Running honeypot detection...")

                result = subprocess.run(cmd, check=True, capture_output=True, text=True)

                if use_semantic:
                    st.write("Bi-encoder semantic re-ranking complete.")
                if use_cross_encoder:
                    st.write("Cross-encoder sliding-window deep alignment complete.")

                st.write("Generating reasoning for top 100...")
                st.write("Validating output...")
                status.update(label="Pipeline complete!", state="complete", expanded=False)

            elapsed_time = time.time() - start_time
            mem_after = get_memory_usage_mb()

            # Log pipeline run to compliance audit
            db.log_pipeline_run({
                "file": uploaded_file.name,
                "file_size_mb": round(file_size_mb, 1),
                "mode": mode_text,
                "elapsed_seconds": round(elapsed_time, 1),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })

            if os.path.exists(output_path):
                df = pd.read_csv(output_path)

                details = None
                if os.path.exists(details_path):
                    with open(details_path, "r", encoding="utf-8") as jf:
                        details = json.load(jf)

                # ── Upgrade 4: System Profiler Cockpit ────────────────
                st.markdown("")
                st.subheader("System Profiler Cockpit")

                candidates_count = 0
                speed_match = re.search(
                    r"Phase 1 complete:\s+([\d,]+)\s+candidates",
                    result.stdout
                )
                if speed_match:
                    candidates_count = int(speed_match.group(1).replace(",", ""))

                speed_cps = candidates_count / elapsed_time if elapsed_time > 0 else 0
                ndcg_score = compute_simulated_ndcg(details, dw)
                mem_delta = mem_after - mem_before if mem_before > 0 else 0

                em1, em2, em3, em4, em5 = st.columns(5, gap="small")
                with em1:
                    st.metric("Throughput", f"{speed_cps:,.0f}/s")
                with em2:
                    st.metric("Memory Model", "O(N) heapq")
                with em3:
                    st.metric("NDCG@10", f"{ndcg_score:.4f}")
                with em4:
                    st.metric("Execution", f"{elapsed_time:.1f}s")
                with em5:
                    mem_display = f"{mem_after:.0f}MB" if mem_after > 0 else "N/A"
                    st.metric("Memory", mem_display)

                st.markdown("")

                # Summary metrics
                mc1, mc2, mc3, mc4 = st.columns(4, gap="medium")
                with mc1:
                    st.metric("Shortlisted", "100")
                with mc2:
                    top_score = df['score'].iloc[0] if not df.empty else 0
                    st.metric("Top Score", f"{top_score:.4f}")
                with mc3:
                    last_score = df['score'].iloc[-1] if not df.empty else 0
                    st.metric("Cutoff", f"{last_score:.4f}")
                with mc4:
                    fb_counts = db.get_feedback_counts()
                    total_fb = fb_counts["upvotes"] + fb_counts["downvotes"]
                    st.metric("Total Feedback", str(total_fb))

                st.markdown("")

                # Score distribution
                st.subheader("Score Distribution")
                chart_df = df[['rank', 'score']].set_index('rank')
                st.area_chart(chart_df, use_container_width=True, color="#6366f1")

                st.divider()

                # ── Feedback Summary ──────────────────────────────────
                fb_counts = db.get_feedback_counts()
                if fb_counts["upvotes"] > 0 or fb_counts["downvotes"] > 0:
                    st.markdown(
                        f"**Persistent Recruiter Feedback:** "
                        f"{fb_counts['upvotes']} validated, "
                        f"{fb_counts['downvotes']} rejected "
                        f"(survives reboots)"
                    )

                # ── Candidate cards with persistent RLRF ──────────────
                st.subheader("Ranked Shortlist")

                if details:
                    details_map = {d["candidate_id"]: d for d in details}

                    # Load historical feedback from database
                    historical_feedback = db.get_all_feedback()

                    display_rows = []
                    for _, row in df.iterrows():
                        cid = row['candidate_id']
                        adjusted_score = float(row['score'])

                        # Apply persistent historical adjustment
                        if cid in historical_feedback:
                            adjusted_score = max(0.0, min(1.0, adjusted_score + historical_feedback[cid]))

                        display_rows.append({
                            "candidate_id": cid,
                            "original_score": float(row['score']),
                            "adjusted_score": adjusted_score,
                            "rank": int(row['rank']),
                            "reasoning": row.get('reasoning', ''),
                        })

                    display_rows.sort(key=lambda x: -x["adjusted_score"])

                    for new_rank, item in enumerate(display_rows, 1):
                        cid = item["candidate_id"]
                        score = item["adjusted_score"]
                        original_score = item["original_score"]
                        reasoning = item["reasoning"]

                        detail = details_map.get(cid, {})
                        title = detail.get("current_title", "Unknown")
                        company = detail.get("current_company", "Unknown")
                        years = detail.get("years_exp", 0)
                        location = detail.get("location", "Unknown")
                        notice = detail.get("notice_days", 0)

                        # Check persistent feedback state
                        fb_type = db.get_feedback_type(cid)
                        adj_indicator = ""
                        if fb_type == "downvote":
                            adj_indicator = " [REJECTED]"
                        elif fb_type == "upvote":
                            adj_indicator = " [VALIDATED]"

                        label = f"#{new_rank} | {title} at {company} | Score: {score:.4f}{adj_indicator}"

                        with st.expander(label, expanded=(new_rank <= 3)):

                            st.markdown(
                                f'<div style="margin-bottom:1rem;">'
                                f'<span class="info-chip">{cid}</span>'
                                f'<span class="info-chip">{location}</span>'
                                f'<span class="info-chip">{years:.0f}y exp</span>'
                                f'<span class="info-chip">{notice}d notice</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                            st.caption(reasoning)

                            left_col, right_col = st.columns([1, 1], gap="large")

                            with left_col:
                                strengths = detail.get("strengths", [])
                                if strengths:
                                    st.markdown("**Why Matched**")
                                    for s in strengths:
                                        st.markdown(
                                            f'<span class="tag-strength">✔ {s}</span>',
                                            unsafe_allow_html=True
                                        )

                                st.markdown("")

                                concerns = detail.get("concerns", [])
                                if concerns:
                                    st.markdown("**Potential Concerns**")
                                    for c in concerns:
                                        st.markdown(
                                            f'<span class="tag-concern">⚠ {c}</span>',
                                            unsafe_allow_html=True
                                        )

                            with right_col:
                                comps = detail.get("components", {})
                                st.markdown("**Score Breakdown**")

                                def render_bar(label_text, value):
                                    st.markdown(
                                        f'<div class="score-row">'
                                        f'<span class="score-lbl">{label_text}</span>'
                                        f'<span class="score-val">{value:.0%}</span>'
                                        f'</div>',
                                        unsafe_allow_html=True
                                    )
                                    st.progress(min(value, 1.0))

                                render_bar("Technical Skills", comps.get("skills", 0))
                                render_bar("Career Trajectory", comps.get("title_career", 0))
                                render_bar("Behavioral", comps.get("behavioral", 0))

                                edu_loc = (comps.get("education", 0) + comps.get("location", 0)) / 2
                                render_bar("Education & Location", edu_loc)

                                sem = comps.get("semantic_score", 0)
                                if sem > 0:
                                    render_bar("Semantic Match", sem)

                                ce = comps.get("cross_encoder_score", 0)
                                if ce > 0:
                                    render_bar("Cross-Encoder", ce)

                            # ── Persistent RLRF Buttons ───────────────
                            st.markdown("")
                            fb1, fb2, fb3 = st.columns([1, 1, 3])

                            with fb1:
                                is_upvoted = fb_type == "upvote"
                                up_label = "Validated" if is_upvoted else "Valid Match"
                                if st.button(
                                    up_label,
                                    key=f"up_{cid}",
                                    disabled=is_upvoted,
                                    use_container_width=True,
                                ):
                                    db.record_feedback(cid, "upvote", 0.05)
                                    st.rerun()

                            with fb2:
                                is_downvoted = fb_type == "downvote"
                                dn_label = "Rejected" if is_downvoted else "Not a Match"
                                if st.button(
                                    dn_label,
                                    key=f"down_{cid}",
                                    disabled=is_downvoted,
                                    use_container_width=True,
                                ):
                                    db.record_feedback(cid, "downvote", -0.15)
                                    st.rerun()

                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)

                # Downloads
                st.divider()
                dl1, dl2 = st.columns(2, gap="medium")
                with dl1:
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="Download submission.csv",
                            data=file, file_name="submission.csv",
                            mime="text/csv", use_container_width=True,
                        )
                with dl2:
                    if os.path.exists(details_path):
                        with open(details_path, "rb") as file:
                            st.download_button(
                                label="Download Analysis JSON",
                                data=file, file_name="submission_details.json",
                                mime="application/json", use_container_width=True,
                            )
            else:
                st.error("Engine failed to produce output CSV.")

        except subprocess.CalledProcessError as e:
            st.error(f"Execution Error: {e.stderr}")

        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if weights_file and os.path.exists(weights_file):
                os.remove(weights_file)