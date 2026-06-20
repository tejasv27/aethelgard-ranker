# Aethelgard: Hybrid Hiring Intelligence Engine 🏆
**Built for the Hack2Skill Data & AI Challenge**

Recruiters are overwhelmed by resume inflation and keyword-stuffing. Traditional ATS systems get easily tricked by candidates adding buzzwords out of context. 

**Aethelgard** solves this. It is a high-performance, hybrid AI screening system that processes massive datasets (100,000+ records) efficiently to find candidates who *actually* fit the role based on trajectory, behavior, and semantic understanding.

## 🧠 The Algorithm: How It Works
Aethelgard does not rely on a single black-box AI score. It uses a **Two-Stage Hybrid Pipeline**:

### Stage 1: Deterministic Filtering (Speed & Scale)
To process 100K+ profiles without memory crashes, the engine uses stream processing (`heapq`) to evaluate candidates across 7 distinct dimensions:
1. **Title Alignment (28%)**
2. **Technical Skill Quality (22%)**
3. **Experience Fit (15%)**
4. **Behavioral & Platform Activity (15%)**
5. **Location Preference (8%)**
6. **Career Ownership/Trajectory (7%)**
7. **Education Quality (5%)**

*🔥 Anti-Cheat (Honeypot Detection):* During this stage, the system actively detects and penalizes profiles with non-technical job titles that keyword-stuff AI/ML buzzwords. 

### Stage 2: Semantic Re-Ranking (Deep Understanding)
The deterministic engine instantly filters the noise down to the Top 500 candidates. Aethelgard then runs an NLP pass using `sentence-transformers` (`all-MiniLM-L6-v2`) to calculate the exact semantic cosine similarity between the Job Description and the candidate's profile, delivering a perfectly ranked Top 100.

## 💻 Tech Stack
* **Core Engine:** Python, `pandas`, `heapq` (Stream Processing)
* **AI / Embeddings:** `sentence-transformers`, PyTorch (CPU-optimized)
* **Frontend UI:** Streamlit with custom Dark Glassmorphism CSS

## 📊 Recruiter-Centric UI
Instead of just showing raw data, the UI generates **Rich Candidate Cards**. When a recruiter clicks on a profile, they see:
* **Why Matched (✔):** Dynamic explanations of their strengths (e.g., "7y experience fits the 5-9y requirement").
* **Potential Concerns (⚠):** Honest flags (e.g., "90-day notice period").
* **Visual Score Breakdown:** Clean progress bars showing exactly how the AI evaluated them.

## 👥 Team
Built by Sneha Paul and Tejasv Sharma.
