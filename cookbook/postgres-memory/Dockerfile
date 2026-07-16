FROM python:3.12-slim

WORKDIR /workspace
COPY . /workspace
RUN pip install --no-cache-dir . \
    && pip install --no-cache-dir "psycopg[binary]>=3.2,<4" \
    && pip install --no-cache-dir --no-deps ./packages/lumis-sdk-postgres-memory

WORKDIR /workspace/cookbook/postgres-memory
ENTRYPOINT ["python", "demo.py"]
