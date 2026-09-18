# Airflow Docker Setup (Phase 1- Dummy Test)

## First-time setup
docker compose up airflow-init
docker compose up -d

## Verify
Open http://localhost:8080 (login: airflow / airflow), un-pause 'dummy_test_dag', trigger it, confirm both tasks turn green.

## Stop
docker compose down