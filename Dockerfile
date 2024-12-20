FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

RUN mkdir -p /app/data && \
    chmod -R 755 /app/src && \
    chmod 777 /app/data

ENV PYTHONPATH=/app
ENV APP_DIR=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "/app/src/main.py"] 