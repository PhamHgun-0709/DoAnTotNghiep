FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Install dependencies
COPY api/requirements.txt /tmp/api_requirements.txt

RUN pip install --no-cache-dir -r /tmp/api_requirements.txt && \
    pip install --no-cache-dir streamlit plotly pandas requests

# Copy application files
COPY giao-dien /app/giao-dien
COPY data /workspace/data

EXPOSE 8501

CMD ["streamlit", "run", "giao-dien/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
