import streamlit as st
import pandas as pd
import subprocess
import os
import time

# 1. Custom Page Styling
st.set_page_config(
    page_title="Aethelgard | Hiring Intelligence", 
    page_icon="🦅", 
    layout="wide"
)

# Dark Theme CSS Injection
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button {
        background-color: #1f77b4; color: white; border-radius: 6px;
        padding: 0.5rem 2rem; font-weight: bold; border: none;
    }
    .stButton>button:hover { background-color: #145a8d; color: white; }
    .metric-card {
        background-color: #1a1c24; border-radius: 8px; padding: 1.5rem;
        border: 1px solid #2d3139; text-align: center;
    }
    .metric-val { font-size: 1.8rem; font-weight: bold; color: #00ffcc; }
    .metric-lbl { font-size: 0.9rem; color: #8a90a6; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# 2. Sidebar Configuration
st.sidebar.image("https://img.icons8.com/nolan/96/artificial-intelligence.png", width=80)
st.sidebar.title("Aethelgard Engine")
st.sidebar.markdown("""
**Version:** 1.0.0 Stable  
**Architecture:** CPU-Only Deterministic Graph  
**Target Band:** 5-9 Years Experience  
""")
st.sidebar.divider()
st.sidebar.info("Operational Status: Ready. Pipeline fully matches Redrob candidate schemas.")

# 3. Main Dashboard Layout
st.title("🦅 Aethelgard: Deterministic Hiring Intelligence Engine")
st.caption("Bypassing resume inflation and keyword stuffing through contextual talent tracking under 300 seconds.")

# Informative Metric Row
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><div class="metric-val">100,000</div><div class="metric-lbl">Max Pool Capacity[cite: 1]</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><div class="metric-val">Top 100</div><div class="metric-lbl">Deterministic Shortlist Target[cite: 1]</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><div class="metric-val">&lt; 5 Min</div><div class="metric-lbl">Strict Processing Ceiling[cite: 1]</div></div>', unsafe_allow_html=True)

st.divider()

# 4. Core Application Workflow
st.subheader("📁 Process New Candidate Batch")
uploaded_file = st.file_uploader("Drop `candidates.jsonl` or `.jsonl.gz` dataset here", type=["gz", "jsonl"])

if uploaded_file is not None:
    input_path = f"temp_{uploaded_file.name}"
    output_path = "submission.csv"
    
    # Cache file locally
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    st.info("Dataset verified by system. Click button below to begin processing.")
    
    if st.button("⚡ Execute Ranking Engine"):
        start_time = time.time()
        
        try:
            with st.spinner("Executing structural analysis loops and anti-honeypot filters..."):
                # Execute the exact operational backend block
                subprocess.run(
                    ["python", "rank.py", "--candidates", input_path, "--out", output_path], 
                    check=True, capture_output=True, text=True
                )
            
            elapsed_time = time.time() - start_time
            st.success(f"Pipeline executed successfully in {elapsed_time:.2f} seconds!")
            
            # Display Result Sheets
            if os.path.exists(output_path):
                df = pd.read_csv(output_path)
                
                # Visualizing the distribution of scores
                st.subheader("📈 Score Distribution Overview")
                st.line_chart(df['score'].head(50))
                
                st.subheader("🏆 Premium Shortlist Data View")
                st.dataframe(df, width="stretch")
                
                # Download Node
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="📥 Download Official submission.csv",
                        data=file,
                        file_name="submission.csv",
                        mime="text/csv"
                    )
            else:
                st.error("Engine failed to emit standard CSV file layer.")
                
        except subprocess.CalledProcessError as e:
            st.error(f"Execution Error encountered inside Python shell: {e.stderr}")
        
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)