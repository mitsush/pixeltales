FROM python:3.10-slim-bookworm

WORKDIR /app

COPY .. /app

RUN pip install --no-cache-dir -r requirements.txt
