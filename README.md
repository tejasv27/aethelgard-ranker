# Aethelgard 🏆

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?style=for-the-badge&logo=streamlit)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge)

**Built for the Hack2Skill Data & AI Challenge**

## 🚀 Problem Statement
The collapse of traditional ATS keyword-matching has led to the rise of AI-driven "resume inflation" and honeypot profiles. Recruiters are overwhelmed by candidates who keyword-stuff modern AI/ML terms without the actual trajectory or experience to back it up. 

## 💡 Why This Matters
Finding the true signal in massive datasets (100,000+ candidates) requires a system that can bypass superficial keywords. Aethelgard enables recruiters to screen at scale without false positives, optimizing for actual engineering capability and alignment.

## ✨ Features
- **Honeypot Detection:** Active penalization of profiles with non-technical job titles that keyword-stuff AI/ML buzzwords.
- **Explainable AI Cards:** Expandable candidate cards displaying exact strengths, concerns, and a visual score breakdown.
- **RLRF Feedback Loops:** Persistent Reinforcement Learning from Recruiter Feedback.
- **System Profiler Cockpit:** Live dashboard tracking Candidates/Sec, Memory Usage, and NDCG@10 alignment.

## 🏗 AI & System Architecture
Aethelgard operates on an optimized **4-Stage Hybrid Pipeline**:

![Aethelgard Architecture Flowchart](docs/assets/architecture_flowchart.png)

1. **Phase 1: Dynamic Initialization:** Gemini 2.5 Flash processes the Job Description first to generate strict Pydantic schemas. These dynamic weights are then passed to the ranking engine.
2. **Phase 2: Deterministic Engine:** The O(N) heapq architecture streams 100K+ records safely, scoring candidates and outputting the "Top 200 Shortlist".
3. **Phase 3: Cross-Encoder Reranking:** The deep semantic alignment layer is applied to the Top 200 Shortlist. It uses "Sliding Window + Max Pooling" to overcome the 512-token limit and evaluate deep contextual fit.
4. **Phase 4: SQLite RLRF:** The final processing gate. Persistent Reinforcement Learning from Recruiter Feedback (👍/👎) is committed to a local SQLite database, applying adjustments before outputting the Final Ranked Output.

## 🔄 Workflow & Folder Structure

```text
📁 aethelgard/
├── 📄 app.py              # Streamlit SaaS Interface & Cockpit
├── 📄 rank.py             # Deterministic O(N) Engine + Semantic Pipeline
├── 📄 ai_core.py          # LLM Weight Configuration via Gemini
├── 📄 database.py         # SQLite Persistence & RLRF
├── 📄 requirements.txt    # Dependency Manifest
├── 📄 test_scoring.py     # Smoke Tests & Validation
├── 📄 release.sh          # CI/CD Deployment Script
└── 📁 docs/               # Advanced Architecture & Setup Docs
```

## 🛠 Technology Stack
- **Core Engine:** Python 3.9+, standard library (`heapq`, `sqlite3`).
- **UI:** Streamlit, Pandas.
- **AI/ML:** sentence-transformers (`cross-encoder/ms-marco-MiniLM-L-6-v2`), PyTorch.
- **Generative AI:** `google-genai` (Gemini 2.5 Flash).
- **Profiling:** `psutil`.

## 📦 Installation & Configuration
```bash
git clone https://github.com/tejasv27/aethelgard-ranker.git
cd aethelgard-ranker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### ⚙️ Local Development Setup

To run Aethelgard locally, you must provide your own Gemini 2.5 Flash API key via a local environment variable.

1. **Configure the AI Environment:**
   * Create a new file in the root directory named exactly `.env`.
   * Add your Google Gemini API key to the file:
     ```env
     GEMINI_API_KEY="your_actual_api_key_here"
     ```
   *(Note: The `.env` file is safely ignored by Git to protect your credentials.)*

2. **Launch the Engine:**
   ```bash
   streamlit run app.py
   ```
*Aethelgard requires no external databases. SQLite is automatically initialized locally.*

## 📚 API Documentation & Architecture
Please refer to [docs/API_REFERENCE.md](docs/API_REFERENCE.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 🔮 Future Scope
- Integration with external ATS systems (Workday, Greenhouse).
- Multi-modal JD processing (e.g., matching candidates to recorded hiring manager calls).
- Distributed processing for datasets > 10M records.

## 👥 Team Members
- **Sneha Paul**
- **Tejasv Sharma**

## 📜 License & Acknowledgements
MIT License. Built for the Hack2Skill Data & AI Challenge.
