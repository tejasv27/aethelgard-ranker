# Pitch Deck Notes

## Demo Script
1. **Introduction:** Briefly define "resume inflation" and the limitation of standard ATS systems.
2. **Ingestion & JD Weighting:** Show the Streamlit UI. Paste a complex Job Description. Click "Generate AI Weights" and watch the sliders dynamically adjust based on Gemini's structured output.
3. **Execution:** Upload the dataset. Start the engine. Point out the "System Profiler Cockpit" highlighting the O(N) throughput (Candidates/Second).
4. **Honeypot Highlight:** Show the Honeypot Demo Card. Explain how a standard ATS gets tricked, but Aethelgard drops the candidate's score.
5. **Deep Alignment:** Explain the Cross-Encoder Sliding Window approach.
6. **RLRF Action:** Click a thumbs down on a candidate, showing the persistent SQLite tracking updating in real-time.

## Anticipated Questions
- *Q: How do you handle Gemini API rate limits?*
  - A: We implemented a 3-tier fallback strategy (Structured Schema -> Freetext Parsing -> Hardcoded Defaults). The system never crashes.
- *Q: Why not use an LLM for all 100K candidates?*
  - A: It would be too slow and expensive. Our Stage 1 deterministic engine is mathematically O(N) bounded, providing sub-minute execution before applying heavy semantic models.
- *Q: How do you bypass the 512-token limit of the Cross-Encoder?*
  - A: We built a sliding window tokenizer that chunks long profiles and applies max-pooling, ensuring no deep technical experience is truncated.
