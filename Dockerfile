# Usa una imagen base de Python
FROM python:3.8

# Instala Apache Airflow
RUN pip install "apache-airflow==2.7.0" \
  && python -m pip install pandas \
  && python -m pip install python-dotenv \
  && python -m pip install psycopg2

# Configura las variables de entorno para Airflow
ENV AIRFLOW_HOME=/root/airflow
ENV PYTHONPATH="${PYTHONPATH}:${AIRFLOW_HOME}"
ENV AIRFLOW_DB_MIGRATE=true

# Crea el directorio de DAGs y copia tu archivo al directorio de DAGs
RUN mkdir -p /root/airflow/dags
RUN mkdir -p /root/airflow/logs
RUN mkdir -p /root/airflow/keys

COPY ./dags/TP_Final_Dag.py /root/airflow/dags/TP_Final_Dag.py
COPY ./dags/config.ini /root/airflow/dags/config.ini
COPY Credentials.env /root/airflow/keys/Credentials.env

RUN airflow db migrate
RUN airflow users create \
		--username airflow \
        --password airflow \
        --firstname Marina \
        --lastname Zambrano \
		--role Admin \
        --email admin@example.org 

# Comando para iniciar la interfaz web y los procesos de Airflow
CMD ["bash", "-c", "airflow webserver --port 8080 & airflow scheduler"]