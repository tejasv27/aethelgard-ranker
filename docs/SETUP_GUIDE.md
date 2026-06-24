# Setup Guide

### 1. Prerequisites
- Python 3.9 or higher
- Git

### 2. Installation
```bash
git clone https://github.com/aethelgard/aethelgard.git
cd aethelgard
python -m venv venv
# Activate virtual environment
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables
You must provide a Google Gemini API key to enable dynamic weight generation.
```bash
export GOOGLE_API_KEY="your-api-key"
```

### 4. Running the App
```bash
streamlit run app.py
```
Navigate to `http://localhost:8501`.
