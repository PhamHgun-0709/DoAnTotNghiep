FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY api /workspace/api
COPY alembic.ini /workspace/alembic.ini
COPY alembic /workspace/alembic
COPY scripts /workspace/scripts
COPY data /workspace/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8000"]
