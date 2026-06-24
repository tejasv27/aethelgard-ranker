# Deployment Guide

Aethelgard is designed for immediate cloud deployment as a Streamlit SaaS application.

### Streamlit Community Cloud
1. Push the repository to GitHub.
2. Log into Streamlit Community Cloud.
3. Select "New app" -> Deploy from GitHub.
4. Set the main file path to `app.py`.
5. Under "Advanced settings", add your `GOOGLE_API_KEY` to the Secrets management.
6. Deploy.

### Docker Deployment
A minimal Dockerfile is provided:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```
Run with: `docker build -t aethelgard . && docker run -p 8501:8501 -e GOOGLE_API_KEY=key aethelgard`
