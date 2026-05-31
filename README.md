# 0. 디렉토리 생성
mkdir -p dags logs plugins config include
chmod 777 logs plugins config include
chmod 755 dags

# 1. 네트워크 먼저
docker network create auction-network

# 2. DB 먼저 올리고
docker compose -f docker-compose-db.yaml up -d --build

# 3. 그 다음 scheduler (init 포함)
docker compose -f docker-compose-airflow-scheduler.yaml up -d

# 4. 마지막 worker
docker compose -f docker-compose-airflow-worker.yaml up -d