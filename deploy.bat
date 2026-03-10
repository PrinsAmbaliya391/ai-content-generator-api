@echo off

<<<<<<< HEAD
:: Deployment script for the AI Content Generator
:: This script stops existing containers, builds new ones, and flows logs.

echo "Clear Screen"
cls

echo "DOCKER DOWN: Stopping and removing containers..."
docker compose down --remove-orphans

echo "DOCKER UP: Building and starting containers in detached mode..."
docker compose up --build -d

echo "DOCKER PS: Verifying container status..."
=======
echo "Clear Screen"
cls

echo "DOCKER DOWN"
docker compose down --remove-orphans

echo "DOCKER UP"
docker compose up --build -d

echo "DOCKER PS"
>>>>>>> bb1d64e96c32bb861b35557a0b54ee61969be875
docker ps

echo "FOLLOWING LOGS (Ctrl+C to exit logs)"
docker logs -f fastapi-ai-api