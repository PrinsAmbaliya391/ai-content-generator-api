@echo off

echo "Clear Screen"
cls

echo "DOCKER DOWN"
docker compose down --remove-orphans

echo "DOCKER UP"
docker compose up --build -d

echo "DOCKER PS"
docker ps

echo "FOLLOWING LOGS (Ctrl+C to exit logs)"
docker logs -f fastapi-ai-api