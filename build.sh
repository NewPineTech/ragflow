docker build --platform linux/arm64 -t newpinetech/ragflow:v1.2 -f Dockerfile . && cd docker  && docker compose -f docker-compose.yml  up -d --build --remove-orphans
