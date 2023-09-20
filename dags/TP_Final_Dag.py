#!/usr/bin/env python

#Librerias
import pandas as pd
import requests
import numpy as np
import os
import psycopg2
from pandas import json_normalize
from dotenv import load_dotenv

import smtplib
import ssl
from email import message
import configparser

# Airflow
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
from datetime import timedelta

def send_email(login_user, login_pass,email_to,subject,body_text):
    try:
        from email.message import EmailMessage
        email = EmailMessage()
        email["From"] = login_user
        email["To"] = email_to
        email["Subject"] = subject
        email.set_content(body_text)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(login_user, login_pass)
            smtp.sendmail(login_user, email_to, email.as_string())
            print('Alerta Enviado!')
    except Exception as exception:
        print(exception)
        return "Error while sending email alert."
    return "Mensaje enviado!"

def get_data_from_API(**context):
    
    #Conexion con API y obtencion de datos 
    params = {
        'access_key': '4c98ca94efdfdd7bfa31e798d616d57c'
    }

    df = pd.DataFrame()

    try:
        print('Adquiriendo datos...')
        #Request
        api_result = requests.get('http://api.aviationstack.com/v1/flights', params)
        if api_result:
            #Convertir en Dataframe
            results = api_result.json()
            if "data" in results:
                data = results.get('data')
                # Filtra el json para eliminar informacion de objetos que no voy a usar
                for vuelo in data:
                    del(vuelo['aircraft'])
                    del(vuelo['live'])
    
                df = json_normalize(data)
                print('Information obtained successfully from API!')       
        else:
            print('An error has occurred.') 
    except ValueError as e:
        print(e)
        raise e

    print('Continue with transformation of data...')

    #Transformo y limpio los datos
    df = df.drop(['departure.icao', 'departure.gate', 'departure.estimated', 'departure.actual','departure.estimated_runway',
              'departure.actual_runway', 'arrival.icao', 'arrival.gate', 'arrival.baggage', 'arrival.scheduled', 'arrival.estimated',
               'arrival.estimated_runway', 'arrival.actual_runway', 'airline.icao', 'flight.icao','flight.codeshared', 'flight.codeshared.airline_name',
               'flight.codeshared.airline_iata', 'flight.codeshared.airline_icao', 'flight.codeshared.flight_number', 'flight.codeshared.flight_iata',
               'flight.codeshared.flight_icao', 'arrival.terminal', 'arrival.actual', 'arrival.timezone'], axis=1)

    df['departure.delay']  = df['departure.delay'].fillna(0)
    df['arrival.delay']  = df['arrival.delay'].fillna(0)
    df['departure.terminal']  = df['departure.terminal'].fillna('Unknown')
    df['departure.delay'] = df['departure.delay'].astype(int)
    df['arrival.delay'] = df['arrival.delay'].astype(int)
    # Convert the "DateColumn" to a date format
    df["flight_date"] = pd.to_datetime(df["flight_date"])
    # Convierte la columna "departure.scheduled" al tipo de dato datetime
    df["departure.scheduled"] = pd.to_datetime(df["departure.scheduled"], format="%Y-%m-%dT%H:%M:%S%z")
    df = df.dropna()

    #Guardo los datos en un archivo
    csv_filename = f"{context['ds']}_datos.csv"
    context['ti'].xcom_push(key='File_name',value=csv_filename)
    df.to_csv(csv_filename, index=False)
    print('Information transformed successfully!!')
    return 0

def save_information(**context):
    # Ruta hacia el archivo .env en carpeta keys
    env_path = '/root/airflow/keys/Credentials.env'

    # Cargar las variables de entorno desde el archivo .env
    load_dotenv(env_path)

    # Configurar las variables de conexión
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_DATABASE = os.getenv('DB_DATABASE')

    print('Trying database connection...')
    #Conexion Con Base de Datos
    try:
        db_conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE
        )
        print("Connected to database successfully!")

        # Crear un cursor
        cursor = db_conn.cursor()

        #Cargo los datos a guardar
        csv_filename = context['ti'].xcom_pull(key='File_name',task_ids='Extraction_Process')
        df = pd.read_csv(csv_filename)

        # Convertir los datos del DataFrame en una lista de tuplas para acelerar el insert posterior
        data = [tuple(row) for row in df.to_numpy()]

        # Ejecutar el insert con executemany
        columns = ['flight_date','flight_status','departure_airport','departure_timezone','departure_iata',      
        'departure_terminal','departure_delay','departure_scheduled','arrival_airport','arrival_iata',     
        'arrival_delay','airline_name','airline_iata','flight_number','flight_iata']         
        
        table_name = 'vuelos'
        
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES %s"

        upsert_sql = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (flight_date, flight_iata, departure_iata, arrival_iata)
            DO UPDATE SET
            flight_status = excluded.flight_status,  
            departure_terminal = excluded.departure_terminal,
            departure_delay = excluded.departure_delay,
            departure_scheduled = excluded.departure_scheduled,
            arrival_delay = excluded.arrival_delay
            """

        from psycopg2.extras import execute_values

        #Comienzo mi transaccion    
        cursor.execute("BEGIN")

        #Borro todos los registros actuales de la tabla
        #cursor.execute(f"TRUNCATE {table_name}")

        #Inserto nuevamente los valores de la tabla
        execute_values(cursor, upsert_sql, data)

        #Si todo salio bien, comiteo los cambios en mi base de datos
        cursor.execute("COMMIT") 

        print("Data inserted successfully!")
        print("Finishing process...")
        
        # Cerrar el cursor y la conexión
        cursor.close()
        db_conn.close()
    
    except Exception as e:
        print("Error with db connection")
        print(e)
        raise e

def verify_delay_and_send_alert(**context):
    #Tomo los datos a analizar
    csv_filename = context['ti'].xcom_pull(key='File_name',task_ids='Extraction_Process')
    df = pd.read_csv(csv_filename)

    print (f"Se levanto un archivo con {df.shape[0]} elementos.")
    # Crea un objeto ConfigParser
    config = configparser.ConfigParser()

    # Lee el archivo INI
    config.read('/root/airflow/dags/config.ini')

    # Obtiene el diccionario de aerolíneas del archivo INI
    aerolineas_config = dict(config['aerolineas'])

    # Recorre uno a uno los valores y los imprime
    demorados = 0
    vuelos_demorados = pd.DataFrame()
    fecha_ejecucion = context['ds']
    subject = f"Mensaje Informacion - Vuelos demorados al dia {fecha_ejecucion}"
    message = "Alertas por vuelos demorados al dia de la fecha:\n\n"

    for aerolinea, min_delay in aerolineas_config.items():
        min_delay = int(min_delay)
        if (min_delay < 0):
            min_delay = 0

        if aerolinea.upper() != "ALL":
            vuelos_demorados = df.loc[(df['airline.iata'] == aerolinea) & (df['departure.delay'] >= min_delay), :]
        else:
            vuelos_demorados = df.loc[(df['departure.delay'] >= min_delay), :]

        demorados = vuelos_demorados.shape[0] 

        if not vuelos_demorados.empty:
            # Si hay resultados, se agregan los datos al mensaje del email
            for index, row in vuelos_demorados.iterrows():
                text_demorado = f"""Vuelo {row['flight.iata']} // {row['airline.name']}
                // Desde: {row['departure.airport']} * Hacia: {row['arrival.airport']} 
                - Despegue demorado {row['departure.delay']} minutos.\n"""
                message += text_demorado
        else:
            print("No se encontraron vuelos demorados.")

        message += (f"\n Total vuelos con demoras mayores a {min_delay} minutos del dia: {demorados} vuelos.\n")
    
    # Obtiene el diccionario de aerolíneas del archivo INI
    sender_email = config['alerts']['smtp_user']
    sender_pass = config['alerts']['smtp_pass']
    to_email = config['alerts']['send_alert_to_emails']
    
    sg = send_email(sender_email, sender_pass,to_email,subject,message)
    print(sg)

# argumentos por defecto para el DAG
default_args = {
    'owner': 'Maru',
    'start_date': datetime(2023,9,1),
    'retries':3,
    'retry_delay': timedelta(minutes=1)
}

with DAG(
    dag_id='TP_Final',
    default_args=default_args,
    description='Obtiene datos de la API de forma diaria. Actualiza la BD y envia alertas por demoras',
    schedule_interval="@daily",
    catchup=False
) as dag:

    # Tareas
    Extraction_Process = PythonOperator(
    task_id='Extraction_Process',
    python_callable=get_data_from_API,
    provide_context = True
    )

    Save_Data_Process = PythonOperator(
    task_id='Save_Data_Process',
    python_callable=save_information,
    provide_context = True
    )

    Send_Alerts_Process = PythonOperator(
    task_id='Send_Alerts_Process',
    python_callable=verify_delay_and_send_alert,
    provide_context = True
    )

# Definicion orden de tareas
Extraction_Process >> Save_Data_Process
Extraction_Process >> Send_Alerts_Process