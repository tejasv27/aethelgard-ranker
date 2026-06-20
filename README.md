# Aethelgard: Hybrid Hiring Intelligence Engine 🏆
**Built for the Hack2Skill Data & AI Challenge**

Aethelgard is a high-performance, hybrid AI candidate screening system designed to solve the critical problem of **resume inflation and keyword-stuffing**. It processes massive datasets (100,000+ records) efficiently while providing deep, recruiter-aligned explainability.

---

## 📖 The Problem We Solve
Traditional Application Tracking Systems (ATS) rely heavily on keyword matching. This creates a massive flaw: candidates who keyword-stuff their resumes (e.g., adding "PyTorch, AWS, LLMs") but lack actual engineering experience (e.g., holding a non-technical role like "Marketing Manager") can bypass the filter and rank highly. 

**Aethelgard fixes this** by applying a multi-signal deterministic engine that cross-references a candidate's *title alignment* and *career trajectory* against their raw skills, punishing "honeypot" profiles while bubbling up genuine talent.

---

## 🚀 Core Features (V2 Architecture)

* **Hybrid Intelligence Pipeline:** Blazes through 100K profiles using a 7-dimension deterministic engine to isolate the Top 500. It then applies an optional NLP semantic re-ranking pass (`sentence-transformers/all-MiniLM-L6-v2`) for absolute precision.
* **Recruiter-Centric Explainability:** Replaces black-box AI scores with an interactive UI. Every candidate profile details specific "Strengths" (✔) and "Potential Concerns" (⚠), alongside visual score breakdowns.
* **Honeypot Detection (Anti-Cheat):** Intelligently flags and rejects "Keyword Stuffers" by heavily weighting title alignment (28%) and career trajectory over pure skill matching.
* **Positive Framing:** Prioritizes candidates demonstrating end-to-end ownership, autonomous technical contribution, and product engineering impact.
* **Premium SaaS UI:** A minimalist, dark-glass Streamlit interface designed for maximum readability, featuring interactive score distributions and a deceptive-profile demo mode.

---

## 🧠 Architecture & Workflow

How Aethelgard processes 100,000 candidates in under 5 minutes:

1. **Stream Processing:** Reads `candidates.jsonl.gz` sequentially to maintain a minimal memory footprint.
2. **7-Dimension Deterministic Scoring:** Calculates scores across 7 critical axes:
   - **Title Alignment (28%):** Does their current/past title match a Senior AI Engineer?
   - **Technical Skill Quality (22%):** Do they have verified, high-quality AI/ML skills?
   - **Experience Fit (15%):** Are they within the 5-9 years sweet spot?
   - **Behavioral & Platform Activity (15%):** Are they active and engaged?
   - **Location Preference (8%):** Do they match required locations (e.g., Pune)?
   - **Career Ownership/Trajectory (7%):** Do they have a trajectory showing product engineering impact?
   - **Education Quality (5%):** Do they have a relevant CS/Engineering degree?
3. **Semantic NLP Pass (Optional):** Takes the Top 500 deterministic winners and computes cosine similarity against the Job Description using PyTorch and `sentence-transformers`.
4. **Data Export:** Outputs the Top 100 to `submission.csv` and generates rich AI explanations into `submission_details.json`.
5. **UI Rendering:** The Streamlit frontend parses the JSON to build rich, interactive candidate cards.

---

## ⚙️ Setup & Installation

Follow these steps to run Aethelgard locally.

### Prerequisites
- Python 3.10+
- Git

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/tejasv27/aethelgard-ranker.git
   cd aethelgard-ranker
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Dashboard:**
   ```bash
   streamlit run app.py --server.maxUploadSize 1000
   ```
   *(Note: The `--server.maxUploadSize` flag is required if you are uploading datasets larger than 200MB).*

### CLI Usage (Headless Mode)
You can run the engine directly from the terminal without the UI:
```bash
# Standard deterministic run
python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv

# Run with Semantic Re-ranking enabled
python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv --semantic
```

---

## 🛠️ Tech Stack
* **Backend Engine:** Python, `pandas`, `heapq` (stream processing)
* **Semantic Layer:** `sentence-transformers`, `PyTorch`
* **Frontend Dashboard:** `Streamlit` with custom injected dark-mode CSS

---

## 👥 Team
Built by **Tejasv Sharma, Aman Kumar, Awi Kumari**, and team for the Hack2Skill Data & AI Challenge.
