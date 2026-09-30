FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home api && mkdir /app/data && chown api:api /app/data
COPY --chown=api:api . .
USER api
ENV DATABASE_PATH=/app/data/feriados.sqlite3
EXPOSE 8000
CMD ["sh", "-c", "python seed.py --inicio 2026 --fim 2030 && exec python -m uvicorn app:app --host 0.0.0.0 --port 8000"]
