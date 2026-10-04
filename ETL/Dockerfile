# syntax=docker/dockerfile:1
#
# ETL image: Airflow (orchestration) + PySpark (transform.py, security_scanner.py)
# + the Kafka consumer (kafka/consumer.py).
# Build context: repository root (needs ETL/ and shared database/ package).
#
# Runs ETL roles in docker-compose.yml: airflow-init, airflow-webserver,
# airflow-scheduler, airflow-worker, etl-consumer, and etl-spark-test.

FROM apache/airflow:2.10.4-python3.11

USER 0
# PySpark needs a JVM runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jdk-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# pgs-db requires SQLAlchemy 2.x, while Airflow 2.10 requires SQLAlchemy < 2.0.
# Isolate pgs-db and kafka-python in /opt/etl-venv for ETL ingestion code.
COPY database/constraints.txt database/pyproject.toml database/README.md /tmp/pgs-db/
COPY database/src /tmp/pgs-db/src
COPY --chown=airflow:0 ETL/kafka/requirements.txt /tmp/etl-kafka-requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/etl-venv \
    && /opt/etl-venv/bin/pip install --disable-pip-version-check \
        --requirement /tmp/etl-kafka-requirements.txt \
        --constraint /tmp/pgs-db/constraints.txt \
        "/tmp/pgs-db[postgres]" \
    && rm -rf /tmp/pgs-db

# Kafka consumer persistent receipt database directory
RUN mkdir -p /data && chown airflow:0 /data && chmod 2775 /data

USER 50000
# Airflow environment for DAG tasks: PySpark 3.5.3 and kafka-python
RUN pip install --no-cache-dir \
        "apache-airflow==${AIRFLOW_VERSION}" \
        pyspark==3.5.3 \
        --requirement /tmp/etl-kafka-requirements.txt \
    && rm /tmp/etl-kafka-requirements.txt

# Copy ETL source directories
COPY ETL/airflow/dags /opt/airflow/dags
COPY ETL/airflow/plugins /opt/airflow/plugins
COPY ETL/airflow/config /opt/airflow/config
COPY ETL/airflow/data /opt/airflow/data
COPY ETL/spark /opt/airflow/spark_lib
COPY ETL/kafka /opt/etl/kafka
