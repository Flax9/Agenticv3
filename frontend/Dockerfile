# Image Nginx berisi build React (masterplan 8.2). Dibangun dengan context root repo
# agar konfigurasi deploy/nginx ikut terbawa:  docker build -f frontend/Dockerfile .

# Stage 1: build React dengan Vite
FROM node:24-alpine AS builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Nginx menyajikan dist/ + reverse proxy /api ke FastAPI
FROM nginx:1.29-alpine
COPY deploy/nginx/snippets/ /etc/nginx/snippets/
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/frontend/dist /usr/share/nginx/html
