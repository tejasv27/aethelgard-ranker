FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860

# Force Streamlit to accept 1000MB uploads
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=1000

# Run with security flags relaxed for Hugging Face iframe compatibility
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]