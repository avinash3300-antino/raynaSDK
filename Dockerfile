FROM python:3.11-slim

# Install Node.js for React bundle build
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build React bundles
COPY web/package.json web/package-lock.json* web/
RUN cd web && npm install

COPY web/ web/
RUN cd web && npm run build

# Copy the rest of the app
COPY . .

# Railway sets PORT env var
ENV PORT=8080
EXPOSE 8080

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT}
