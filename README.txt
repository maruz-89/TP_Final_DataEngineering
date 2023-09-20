# Entrega Trabajo Practico Final

## Alumno 
  Marina Zambrano

## Descripcion
Se adjuntan archivos:

  - Docker-compose.yaml: Se utiliza para levantar los servicios necesarios para correr el tp
  
  - Dockerfile: Dockerfile con el contenido para buildear una imagen que contiene Airflow y todas las dependencias necesarias para correr el script de python.

  - Credentials.env: Archivo con las credenciales y datos necesarios para la conexion con la base de datos.

  - TP_Final_Dag: Script de python que se utiliza para la creacion del dag que se conecta con la API, realiza las transformaciones necesarias e inserta los datos en la tabla.
					Adicionalmente enviar un email de alerta para los vuelos demorados.

  - config.ini: Archivo de configuracion para el funcionamiento del dag. Contiene informacion de la cuenta smpt y parametros para la configuracion de alertas.

  - create_table.sql: Archivo para la creacion de la tabla donde se insertan los datos de los vuelos.
  
## Instrucciones para ejecucion local

### Prerequisitos
  1. Tener instalado Docker.  
  2. La Docker Engine debe estar activa y corriendo.

### Ejecucion
  A continuación se listan los pasos para ejecutar el script:
    1. Abrir una terminal y situarse dentro de la carpeta ppal.
    2. Editar el archivo config.ini que se encuentra en el directorio /dags. Completar los datos de usuario, pass, e emails de alerta.
	  ---
      > [alerts]
	  > smtp_user = <user>
	  > smtp_pass = <password>
	  > send_alert_to_emails = <destinatarios del mail de alerta>
      ---
	3. Levantar los servicios de docker usando el archivo docker-compose
      ---
      > docker-compose up 
      ---
    4. Ingresar a un explorador y acceder al localhost en el puerto 8080
      ---
      http://localhost:8080
      ---
    5. Loguearse a Airflow utilizando las credenciales airflow/airflow
    6. Activar o ejecutar el dag cuyo nombre es: TP_Final
    7. Se puede verificar en la base de datos de postgres los datos insertados en la tabla vuelos

