import streamlit as st
import pandas as pd
import subprocess
import os
import time
import json

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
# Stable Dark SaaS Theme — No expander header CSS overrides
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global typography */
html, body, .main, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Hide Streamlit branding */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* Dark background */
.main, [data-testid="stAppViewContainer"] {
    background-color: #0f1117;
    color: #e8eaed;
}
[data-testid="stSidebar"] {
    background-color: #0f1117 !important;
    border-right: 1px solid #1e1e2e !important;
}

/* Expander card body — do NOT touch the header/summary */
[data-testid="stExpander"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    margin-bottom: 10px;
}

/* Buttons */
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

/* Download buttons */
.stDownloadButton>button {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #34d399; border-radius: 8px; font-weight: 500;
}

/* st.metric */
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

/* Progress bars */
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

/* Strength badges */
.tag-strength {
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 6px; padding: 5px 10px;
    font-size: 0.82rem; display: inline-block;
    margin: 3px 4px 3px 0; line-height: 1.4;
}

/* Concern badges */
.tag-concern {
    background: rgba(251, 191, 36, 0.1);
    color: #fbbf24;
    border: 1px solid rgba(251, 191, 36, 0.2);
    border-radius: 6px; padding: 5px 10px;
    font-size: 0.82rem; display: inline-block;
    margin: 3px 4px 3px 0; line-height: 1.4;
}

/* Info chip */
.info-chip {
    display: inline-block;
    background: #21262d;
    border-radius: 6px; padding: 4px 10px;
    font-size: 0.78rem; color: #8b949e;
    margin-right: 6px; margin-bottom: 6px;
}

/* Score row */
.score-row {
    display: flex; justify-content: space-between;
    align-items: center; margin-top: 10px; margin-bottom: 3px;
}
.score-lbl { font-size: 0.82rem; color: #8b949e; }
.score-val { font-size: 0.82rem; font-weight: 600; color: #e8eaed; }

/* Hero cards */
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

/* Pipeline badge */
.pipe-badge {
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 4px; padding: 4px 12px;
    display: inline-block;
    font-size: 0.7rem; color: #a5b4fc;
    letter-spacing: 0.06em; font-weight: 500;
    text-transform: uppercase;
}

/* Honeypot demo boxes */
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

/* Dividers */
hr { border-color: #21262d !important; }

/* File uploader */
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
    st.caption("Hiring Intelligence Engine")
    st.divider()

    st.markdown("""
**Version:** 2.0.0 Hybrid  
**Architecture:** Deterministic + Semantic  
**Target Band:** 5-9 Years Experience
""")
    st.divider()

    use_semantic = st.toggle("🧠 Semantic Re-Ranking", value=False,
        help="Adds a sentence-transformers pass on top 500 candidates.")

    show_honeypot_demo = st.toggle("🕵️ Deceptive Profile Demo", value=False,
        help="See how Aethelgard catches keyword-stuffed profiles.")

    st.divider()
    st.success("Pipeline Ready")


# ---------------------------------------------------------------------------
# Main Header
# ---------------------------------------------------------------------------
st.markdown("# 🦅 Aethelgard")
st.markdown('<span class="pipe-badge">HYBRID DETERMINISTIC + SEMANTIC INTELLIGENCE</span>', unsafe_allow_html=True)
st.caption("Multi-signal candidate ranking that bypasses resume inflation and keyword stuffing.")

st.markdown("")

m1, m2, m3, m4 = st.columns(4, gap="medium")
with m1:
    st.markdown('<div class="hero-card"><div class="hero-val">100K</div><div class="hero-lbl">Max Candidate Pool</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown('<div class="hero-card"><div class="hero-val">Top 100</div><div class="hero-lbl">Shortlist Output</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown('<div class="hero-card"><div class="hero-val">&lt; 5 min</div><div class="hero-lbl">Processing Time</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown('<div class="hero-card"><div class="hero-val">7 + 1</div><div class="hero-lbl">Scoring Dimensions</div></div>', unsafe_allow_html=True)

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
            "Title Alignment (28%)",
            "Skill Quality (22%)",
            "Experience Fit (15%)",
            "Behavioral (15%)",
            "Location (8%)",
            "Career Ownership (7%)",
            "Education (5%)",
        ],
        "Standard ATS": ["—", "0.95", "—", "—", "—", "—", "—"],
        "Aethelgard": ["0.00", "0.42", "0.90", "0.72", "1.00", "0.95", "0.65"],
        "Verdict": [
            "Marketing != AI Engineer",
            "No career backing for skills",
            "8y in range",
            "Active on platform",
            "Pune preferred",
            "Product company",
            "MBA Marketing",
        ]
    }
    st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, width=0)

    st.info(
        "**Key Insight:** A keyword-matching ATS ranks this candidate #3. "
        "Aethelgard's title alignment signal (28% weight) catches the mismatch — "
        "Marketing Manager has never held an AI/ML role. "
        "Score drops from ~0.95 (ATS) to ~0.09 (Aethelgard)."
    )
    st.divider()


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
    mode_text = "Semantic + Deterministic" if use_semantic else "Deterministic"
    st.info(f"**{uploaded_file.name}** ({file_size_mb:.1f} MB) — Mode: {mode_text}")

    if st.button("Execute Ranking Engine", use_container_width=True):
        start_time = time.time()

        try:
            with st.status("Running Aethelgard pipeline...", expanded=True) as status:
                st.write("Loading candidate dataset...")
                cmd = ["python", "rank.py", "--candidates", input_path, "--out", output_path]
                if use_semantic:
                    cmd.append("--semantic")

                st.write("Extracting features and computing scores...")
                st.write("Running honeypot detection...")

                result = subprocess.run(cmd, check=True, capture_output=True, text=True)

                if use_semantic:
                    st.write("Applying semantic re-ranking on top 500...")

                st.write("Generating reasoning for top 100...")
                st.write("Validating output...")
                status.update(label="Pipeline complete!", state="complete", expanded=False)

            elapsed_time = time.time() - start_time

            if os.path.exists(output_path):
                df = pd.read_csv(output_path)

                # Load details JSON
                details = None
                if os.path.exists(details_path):
                    with open(details_path, "r", encoding="utf-8") as jf:
                        details = json.load(jf)

                # Summary metrics
                st.markdown("")
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
                    st.metric("Time", f"{elapsed_time:.1f}s")

                st.markdown("")

                # Score distribution
                st.subheader("Score Distribution")
                chart_df = df[['rank', 'score']].set_index('rank')
                st.area_chart(chart_df, use_container_width=True, color="#6366f1")

                st.divider()

                # Candidate cards
                st.subheader("Ranked Shortlist")

                if details:
                    details_map = {d["candidate_id"]: d for d in details}

                    for _, row in df.iterrows():
                        cid = row['candidate_id']
                        rank = int(row['rank'])
                        score = float(row['score'])
                        reasoning = row.get('reasoning', '')

                        detail = details_map.get(cid, {})
                        title = detail.get("current_title", "Unknown")
                        company = detail.get("current_company", "Unknown")
                        years = detail.get("years_exp", 0)
                        location = detail.get("location", "Unknown")
                        notice = detail.get("notice_days", 0)

                        # PLAIN text label — no markdown, no HTML, no emojis
                        label = f"#{rank} | {title} at {company} | Score: {score:.4f}"

                        with st.expander(label, expanded=(rank <= 3)):

                            # Info chips
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

                            # Two-column layout
                            left_col, right_col = st.columns([1, 1], gap="large")

                            with left_col:
                                # Strengths
                                strengths = detail.get("strengths", [])
                                if strengths:
                                    st.markdown("**Why Matched**")
                                    for s in strengths:
                                        st.markdown(
                                            f'<span class="tag-strength">✔ {s}</span>',
                                            unsafe_allow_html=True
                                        )

                                st.markdown("")

                                # Concerns
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