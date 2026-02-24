# 🌱 Invernadero IoT — MQTT Seguro con TLS

Proyecto de arquitectura publicador/suscriptor sobre MQTT con autenticación mutua por certificados TLS, almacenamiento en PostgreSQL y despliegue completo en Docker.

---

## 👥 Miembros del equipo

Equipo de 3 personas.

---

## 📖 Explicación de los pasos seguidos

### 1. Punto de partida
El proyecto ya contaba con una arquitectura funcional publicador/suscriptor:
- Un contenedor **productor** (`sensor_tierra`) que simulaba lecturas de sensores de suelo y las publicaba por MQTT.
- Un contenedor **consumidor** (`cerebro_datos`) que se suscribía al broker y almacenaba los datos en PostgreSQL.
- Un broker **Mosquitto** sin ningún tipo de autenticación (puerto 1883, `allow_anonymous true`).

El reto consistía en añadir seguridad real: que solo clientes con certificado válido pudieran conectarse al broker.

### 2. Creación de la Autoridad Certificadora (CA) propia
Se creó un script `generar_certificados.sh` que genera con `openssl` todos los certificados necesarios en la carpeta `certs/`:
- **CA** (`ca.crt` / `ca.key`): la autoridad que firma y valida todos los demás certificados. Actúa como el "sello de confianza" del sistema.
- **Servidor** (`servidor.crt` / `servidor.key`): certificado del broker Mosquitto, con SAN (Subject Alternative Name) para que los clientes puedan verificar su identidad por hostname.
- **Cliente sensor** (`cliente_sensor.crt` / `cliente_sensor.key`): certificado del contenedor productor.
- **Cliente cerebro** (`cliente_cerebro.crt` / `cliente_cerebro.key`): certificado del contenedor consumidor.

### 3. Configuración de Mosquitto con TLS
Se actualizó `mosquitto.conf` para:
- Escuchar en el puerto **8883** (estándar para MQTT sobre TLS) en lugar del 1883.
- Exigir el certificado del servidor (`certfile`, `keyfile`, `cafile`).
- Activar `require_certificate true`: el broker rechaza cualquier cliente que no presente un certificado firmado por nuestra CA.
- Activar `use_identity_as_username true`: el CN del certificado del cliente se usa como su identidad.
- Desactivar el acceso anónimo con `allow_anonymous false`.

### 4. Actualización del código Python
Tanto `simulador_sensor.py` como `guardar_datos.py` se actualizaron para usar TLS al conectarse:
- Se añadió `cliente.tls_set()` con las rutas a `ca.crt`, al certificado del cliente y a su clave privada.
- Se configuró `tls_insecure_set(False)` para verificar que el CN del servidor coincide con su hostname, evitando suplantaciones.

### 5. Actualización del Docker Compose
- Mosquitto se actualizó a la versión `2.0.18` por mejor soporte TLS.
- Se cambió el puerto expuesto a `8883`.
- Los certificados se montan como volúmenes de **solo lectura** (`:ro`) en cada contenedor, en lugar de copiarlos dentro de las imágenes.
- Se añadió `user: "1000:1000"` en Mosquitto para que pueda leer las claves privadas con los permisos correctos.

---

## 🚀 Instrucciones de uso

### Requisitos previos
- Docker y Docker Compose instalados.
- `openssl` disponible en el sistema (viene por defecto en Linux/WSL).
- `mosquitto-clients` para las pruebas desde CLI:
  ```bash
  sudo apt-get install mosquitto-clients
  ```

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd reto_2
```

### 2. Generar los certificados
```bash
chmod +x certs/generar_certificados.sh
./certs/generar_certificados.sh
```

> ⚠️ Este paso debe hacerse **antes** de levantar Docker. Si se levanta Docker sin que existan los certificados, los crea como carpetas vacías y el montaje falla.

### 3. Levantar el proyecto
```bash
docker compose up --build
```

### 4. Probar desde línea de comandos

**Publicar con certificado (debe funcionar):**
```bash
mosquitto_pub \
  -h localhost -p 8883 \
  --cafile certs/ca.crt \
  --cert certs/cliente_sensor.crt \
  --key certs/cliente_sensor.key \
  -t "invernadero/sector_1/suelo" \
  -m '{"sensor_id":"test_cli","temperatura":22.5,"humedad":70.0}' \
  -d
```

**Suscribirse con certificado (debe funcionar):**
```bash
mosquitto_sub \
  -h localhost -p 8883 \
  --cafile certs/ca.crt \
  --cert certs/cliente_cerebro.crt \
  --key certs/cliente_cerebro.key \
  -t "invernadero/#" \
  -d
```

**Sin certificado (debe ser rechazado):**
```bash
mosquitto_pub -h localhost -p 8883 -t "invernadero/prueba" -m "intruso" -d
# Error esperado: A TLS error occurred.
```

### 5. Verificar datos en PostgreSQL
```bash
docker exec -it base_datos psql -U deusto -d invernadero_db
```
```sql
SELECT sensor_id, temperatura, humedad, to_timestamp(fecha/1000) AS hora
FROM mediciones
ORDER BY creado_en DESC
LIMIT 10;
```

---

## ⚠️ Problemas y retos encontrados

### Carpetas en lugar de archivos al montar volúmenes
El problema más recurrente del proyecto. Al ejecutar `docker compose up` sin haber generado los certificados previamente, Docker interpretaba las rutas de los volúmenes (por ejemplo `./certs/ca.crt:/mosquitto/certs/ca.crt`) como directorios y los creaba como carpetas vacías. Al intentar después generar los certificados, `openssl` fallaba con `Is a directory`.

**Solución:** eliminar las carpetas creadas por Docker (`sudo rm -rf certs/`), regenerar los certificados y levantar Docker en el orden correcto. Además, se cambió la estrategia de montaje: en lugar de montar cada archivo individualmente, se monta la carpeta `./certs` entera en cada contenedor, lo que evita este problema completamente.

### La carpeta `/mosquitto/certs` no existía en el contenedor
Aunque el montaje de la carpeta entera resolvía el problema anterior, en un primer intento con montaje de archivos individuales el contenedor de Mosquitto fallaba porque la ruta `/mosquitto/certs/` no existe en la imagen oficial. Docker no puede montar un archivo en una ruta cuya carpeta padre no existe.

**Solución:** montar `./certs:/mosquitto/certs:ro` directamente como carpeta, que Docker sí crea automáticamente.

### Permisos de las claves privadas
Las claves `.key` se generan con permisos `600` (solo lectura para el propietario). Dentro del contenedor Mosquitto, el proceso corría como un usuario diferente y no podía leerlas.

**Solución:** añadir `user: "1000:1000"` en el servicio Mosquitto del Docker Compose para que use el mismo UID que el usuario del host.

### Puerto incorrecto en el consumidor
La variable de entorno `PUERTO_BROKER` se leía como string desde las variables de entorno y se pasaba directamente a `mqtt.Client.connect()`, que espera un entero, causando un error de tipo en tiempo de ejecución.

**Solución:** envolver la lectura con `int()`: `MQTT_PUERTO = int(os.getenv("PUERTO_BROKER", "8883"))`.

---

## 🔭 Posibles vías de mejora

- **Renovación automática de certificados:** los certificados tienen una validez de 10 años, pero en un entorno real se integraría una herramienta como `cert-manager` o Let's Encrypt para renovarlos automáticamente antes de su caducidad.
- **Revocación de certificados (CRL):** actualmente no hay mecanismo para revocar un certificado comprometido sin regenerar toda la CA. Se podría implementar una lista de revocación (CRL) o usar OCSP.
- **Panel de visualización:** añadir Grafana conectado a PostgreSQL para visualizar en tiempo real las métricas del invernadero.
- **Múltiples sensores:** escalar el sistema con más tipos de sensores (CO₂, riego, viento) añadiendo nuevos certificados de cliente y temas MQTT.
- **ACLs por cliente:** configurar listas de control de acceso en Mosquitto para que cada cliente solo pueda publicar o suscribirse a sus propios temas, no a los de otros.
- **Cifrado de la base de datos:** los datos se almacenan en PostgreSQL sin cifrar. En producción se añadiría cifrado en reposo.

---

## 🔀 Alternativas posibles

### Broker MQTT alternativo
En lugar de Mosquitto se podría usar **EMQX** o **HiveMQ**, que ofrecen interfaces web de administración, soporte nativo para clustering y gestión de certificados más avanzada. Mosquitto se eligió por su simplicidad y bajo consumo de recursos.

### Autenticación por usuario/contraseña
Una alternativa más sencilla al sistema de certificados sería usar autenticación básica con usuario y contraseña (`password_file` en Mosquitto). Sin embargo, no ofrece el mismo nivel de seguridad ya que las credenciales pueden filtrarse, mientras que los certificados implican autenticación mutua y cifrado del canal en un solo paso.

### CA externa (Let's Encrypt / HashiCorp Vault)
En lugar de gestionar una CA propia con `openssl`, se podría usar **HashiCorp Vault** como PKI para emitir y gestionar certificados de forma centralizada y auditable. Es la opción habitual en entornos empresariales.

### Base de datos alternativa
En lugar de PostgreSQL se podría usar **InfluxDB**, una base de datos diseñada específicamente para series temporales (exactamente el tipo de datos que generan los sensores), con mejor rendimiento para consultas por rango de tiempo.
