import json
import os
import time
import ssl
import numpy as np
import paho.mqtt.client as mqtt

# Recoge el valor que envía el broker
def leer_config(clave, valor_por_defecto):
    return os.environ.get(clave, valor_por_defecto)

# Función para generar datos realistas por medio de la Distribución Normal (numpy).
def generar_dato(media, variacion):
    valor = np.random.normal(float(media), variacion)
    return round(valor, 2)

def main():
    # Llama a la función leer_config() para cargar todas las variables.
    broker      = leer_config("HOST_BROKER", "localhost")
    puerto      = int(leer_config("PUERTO_BROKER", "8883"))
    tema        = leer_config("TEMA_PUBLICACION", "invernadero/pruebas")
    id_sensor   = leer_config("ID_SENSOR", "sensor_desconocido")
    intervalo   = int(leer_config("INTERVALO", "5"))

    # Valores ideales del cultivo
    temp_media  = float(leer_config("TEMP_IDEAL", "20"))
    hum_media   = float(leer_config("HUMEDAD_IDEAL", "50"))
    luz_media   = float(leer_config("LUZ_IDEAL", "500"))
    ph_medio    = float(leer_config("PH_IDEAL", "7"))

    # Rutas de certificados TLS generados por el .sh, nuestra CA propia
    ruta_ca   = leer_config("RUTA_CA",   "/app/certs/ca.crt")
    ruta_cert = leer_config("RUTA_CERT", "/app/certs/cliente_sensor.crt")
    ruta_key  = leer_config("RUTA_KEY",  "/app/certs/cliente_sensor.key")

    # Configura TLS en el cliente MQTT 
    cliente = mqtt.Client(
        #Asigna un nombre unico
        client_id=id_sensor
    )

    # Configura el SSL
    cliente.tls_set(
        # El cliente verifica que el servidor tiene un certificado firmado por nuestra CA
        ca_certs=ruta_ca,
        #El certificado del cliente
        certfile=ruta_cert,
        #La clave privada del cliente
        keyfile=ruta_key,
        #Forzamos que la version de TLS sea mínimo 1.2
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )

    # Verifica que el Common Name del servidor coincide con su hostname. Para evitar suplantaciones.
    cliente.tls_insecure_set(False)

    print(f"[SENSOR] Conectando a {broker} con TLS")
    try:
        cliente.connect(broker, puerto, 60)
        cliente.loop_start()
        print(f"[SENSOR] Conectado con TLS y listo para enviar datos de {id_sensor}")
    except Exception as e:
        print(f"[SENSOR] Error al conectar: {e}")
        return

    # Envío de datos
    try:
        while True:
            # Crea el paquete de datos
            datos = {
                "sensor_id":   id_sensor,
                "timestamp":   int(time.time() * 1000),
                "temperatura": generar_dato(temp_media, 1.5),
                "humedad":     generar_dato(hum_media, 5.0),
                "luminosidad": generar_dato(luz_media, 50),
                "ph_suelo":    generar_dato(ph_medio, 0.2)
            }

            # Se transforma en JSON para que MQTT lo entienda.
            mensaje_json = json.dumps(datos)

            cliente.publish(tema, mensaje_json)

            print(f"[ENVIADO] 🔒 -> {tema}: {mensaje_json}")

            time.sleep(intervalo)

    # Desconexion
    except KeyboardInterrupt:
        print("[SENSOR] Deteniendo sensor...")
        cliente.loop_stop()
        cliente.disconnect()

if __name__ == "__main__":
    main()
