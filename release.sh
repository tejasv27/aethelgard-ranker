#!/bin/bash
# Aethelgard V5 OMEGA Release Script

# 1. Format & Lint (assumes flake8 or black are available, skipping for raw safety)
# python -m black .

# 2. Stage all modified and new files
git add README.md docs/* app.py rank.py database.py ai_core.py requirements.txt

# 3. Commit with semantic message
git commit -m "feat(core): V5 OMEGA release - sliding window, SQLite RLRF, structured LLM, profiler cockpit"

# 4. Tag the release
git tag -a v5.0.0 -m "Aethelgard V5 OMEGA Grand-Champion Release"

# 5. Push to remote
git push origin main
git push origin v5.0.0

echo "V5 OMEGA successfully deployed to version control."
