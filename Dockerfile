# TACT News — build the Vite SPA, then serve it (and the API) from FastAPI.

# ---- stage 1: build the static frontend ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- stage 2: FastAPI app server ----
FROM python:3.12-slim
WORKDIR /app
# git → pip-install shared-auth from GitHub · ffmpeg → WAV מ-NotebookLM נדחס ל-M4A
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=build /app/dist ./dist
EXPOSE 8000
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
