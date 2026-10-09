FROM python:3.14

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "if [ \"${OTEL_SDK_DISABLED:-true}\" = \"false\" ]; then exec opentelemetry-instrument uvicorn src.api.app:app --host 0.0.0.0 --port 8000; fi; exec uvicorn src.api.app:app --host 0.0.0.0 --port 8000"]