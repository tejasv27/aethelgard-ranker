# Aethelgard: Hybrid Hiring Intelligence Engine 🏆
**Built for the Hack2Skill Data & AI Challenge**

Aethelgard is a high-performance, hybrid AI candidate screening system designed to solve the critical problem of resume inflation and keyword-stuffing. It processes massive datasets (100,000+ records) efficiently while providing deep, recruiter-aligned explainability.

## 🚀 Core Features (V2 Architecture)
* **Hybrid Intelligence Pipeline:** Blazes through 100K profiles using a 7-dimension deterministic engine to isolate the Top 500, then applies optional NLP semantic re-ranking (`sentence-transformers/all-MiniLM-L6-v2`) for absolute precision.
* **Recruiter-Centric Explainability:** Replaces black-box AI scores with an interactive UI. Every candidate profile details specific "Strengths" (✔) and "Potential Concerns" (⚠), alongside visual score breakdowns.
* **Honeypot Detection (Anti-Cheat):** Intelligently flags and rejects "Keyword Stuffers" (e.g., non-technical titles stuffed with AI/ML buzzwords) by cross-referencing trajectory and behavioral signals.
* **Positive Framing:** Prioritizes candidates demonstrating end-to-end ownership, autonomous technical contribution, and product engineering impact.
* **Premium SaaS UI:** A minimalist, dark-glass Streamlit interface designed for maximum readability and a professional user experience.

## 🛠️ Tech Stack
* **Backend Engine:** Python, `pandas`, `heapq` (stream processing)
* **Semantic Layer:** `sentence-transformers`, PyTorch
* **Frontend:** Streamlit with custom injected CSS

## 👥 Team
Built by Tejasv Sharma, Aman Kumar, Awi Kumari, and team.
