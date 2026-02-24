import json
import os
import ssl
import time
import psycopg2
import paho.mqtt.client as mqtt
from datetime import datetime

# Configuración MQTT 
MQTT_BROKER = os.getenv("HOST_BROKER",    "mosquitto")
#Cambia de puerto para el TLS cogiendolo del docker-compose. Vuelve con string y da fallo, por eso en int().
MQTT_PUERTO = int(os.getenv("PUERTO_BROKER", "8883"))
MQTT_TEMA   = os.getenv("TEMA_SUSCRIPCION", "invernadero/#")

# Certificados TLS de consumidor
RUTA_CA   = os.getenv("RUTA_CA",   "/app/certs/ca.crt")
RUTA_CERT = os.getenv("RUTA_CERT", "/app/certs/cliente_cerebro.crt")
RUTA_KEY  = os.getenv("RUTA_KEY",  "/app/certs/cliente_cerebro.key")

# Configuración Base de Datos 
DB_HOST = os.getenv("HOST_BD",    "base_datos")
DB_NAME = os.getenv("NOMBRE_BD",  "invernadero_db")
DB_USER = os.getenv("USUARIO_BD", "deusto")
DB_PASS = os.getenv("CLAVE_BD",   "deusto")


# Intenta entrar en PostgreSQL con usuario y contrasena
def conectar_bd():
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME,
                user=DB_USER, password=DB_PASS
            )
            conn.autocommit = True
            print(f"[BD] Conectado exitosamente a {DB_HOST}")
            return conn
        except Exception as e:
            print(f"[BD] Esperando a la base de datos... ({e})")
            time.sleep(2)

# Si no existe, crea la tabla mediciones
def crear_tabla(conn):
    sql = """
    CREATE TABLE IF NOT EXISTS mediciones (
        id SERIAL PRIMARY KEY,
        sensor_id VARCHAR(50),
        fecha BIGINT,
        temperatura FLOAT,
        humedad FLOAT,
        luminosidad FLOAT,
        ph_suelo FLOAT,
        datos_crudos JSONB,
        creado_en TIMESTAMP DEFAULT NOW()
    );
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    print("[BD] Tabla 'mediciones' verificada/creada.")

#Guarda las lecturas en la Base de datos
def guardar_lectura(conn, datos):
    sql = """
    INSERT INTO mediciones (sensor_id, fecha, temperatura, humedad, luminosidad, ph_suelo, datos_crudos)
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                datos.get("sensor_id"),
                datos.get("timestamp"),
                datos.get("temperatura"),
                datos.get("humedad"),
                datos.get("luminosidad"),
                datos.get("ph_suelo"),
                json.dumps(datos)
            ))
        timestamp_ms = datos.get("timestamp")
        hora_legible = datetime.fromtimestamp(timestamp_ms / 1000.0).strftime('%H:%M:%S')
        print(f"[BD] Guardado -> Sensor: {datos.get('sensor_id')} | Hora: {hora_legible}")
    except Exception as e:
        print(f"[ERROR BD] No se pudo guardar: {e}")

# Avisa al conectarse a MQTT 
def al_conectar(client, userdata, flags, rc):
    print(f"[MQTT] Conectado al broker. Suscribiéndose a {MQTT_TEMA}")
    client.subscribe(MQTT_TEMA)

#Avisa cuando se publica
def al_recibir_mensaje(client, userdata, msg):
    try:
        datos = json.loads(msg.payload.decode("utf-8"))
        guardar_lectura(conn, datos)
    except Exception as e:
        print(f"[ERROR] Mensaje corrupto o error de proceso: {e}")


# Orden real cuando se ejecuta
if __name__ == "__main__":
    # Conectar a la Base de datos
    conn = conectar_bd()
    crear_tabla(conn)

    # Configurar MQTT con TLS 
    cliente_mqtt = mqtt.Client(
        client_id="cerebro_datos"
    )

    # Configurar TLS con los certificados del cerebro)
    cliente_mqtt.tls_set(
        ca_certs=RUTA_CA,
        certfile=RUTA_CERT,
        keyfile=RUTA_KEY,
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )
    cliente_mqtt.tls_insecure_set(False)

    cliente_mqtt.on_connect = al_conectar
    cliente_mqtt.on_message = al_recibir_mensaje

    # Conectar y esperar mensajes
    print(f"[SISTEMA] Conectando a MQTT {MQTT_BROKER} con TLS")
    cliente_mqtt.connect(MQTT_BROKER, MQTT_PUERTO, 60)
    cliente_mqtt.loop_forever()
