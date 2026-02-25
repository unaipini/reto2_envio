
# Genera CA, certificado de broker, certificado cliente sensor y certificado cliente consumidor

# Detiene si hay cualquier error
set -e  

# Busca donde esta el .sh y guarda la ruta
DIRECTORIO="./certs"
DIAS_VALIDEZ=3650  

echo "Generando certificados"


# Crea la CA, Autoridad Certificadora.
echo "Creando la CA (Autoridad Certificadora)"

# Genera la clave de la CA
openssl genrsa -out "$DIRECTORIO/ca.key" 2048

# Generar certificado de la CA
openssl req -new -x509 -days $DIAS_VALIDEZ \
    -key "$DIRECTORIO/ca.key" \
    -out "$DIRECTORIO/ca.crt" \
    -subj "/C=ES/ST=PaisVasco/L=Bilbao/O=Invernadero_CA/CN=CA_Invernadero"

echo "CA creada:" ca.key + " " ca.crt



# Certificado del Broker Mosquitto
echo "Creando certificado del broker"

# Genera la clave del broker
openssl genrsa -out "$DIRECTORIO/servidor.key" 2048

# Se crea la solicitud de firma del broker
openssl req -new \
    -key "$DIRECTORIO/servidor.key" \
    -out "$DIRECTORIO/servidor.csr" \
    -subj "/C=ES/ST=PaisVasco/L=Bilbao/O=Invernadero/CN=mosquitto"

# Crea un archivo temporal para añadir el SAN (Subject Alternative Name)
cat > "$DIRECTORIO/servidor_ext.cnf" <<EOF
[v3_req]
subjectAltName = DNS:localhost, DNS:mosquitto, IP:127.0.0.1
EOF

# La CA firma el certificado del servidor incluyendo la extension SAN.
openssl x509 -req -days $DIAS_VALIDEZ \
    -in "$DIRECTORIO/servidor.csr" \
    -CA "$DIRECTORIO/ca.crt" \
    -CAkey "$DIRECTORIO/ca.key" \
    -CAcreateserial \
    -out "$DIRECTORIO/servidor.crt" \
    -extensions v3_req \
    -extfile "$DIRECTORIO/servidor_ext.cnf"

# Limpiamos el archivo temporal del SAN
rm -f "$DIRECTORIO/servidor_ext.cnf"

echo "Se ha creado el servidor servidor.key + servidor.crt"


# Genera el certificado del CLIENTE, sensor_tierra/productor
echo "Creando certificado del CLIENTE 1, sensor_tierra"

openssl genrsa -out "$DIRECTORIO/cliente_sensor.key" 2048

openssl req -new \
    -key "$DIRECTORIO/cliente_sensor.key" \
    -out "$DIRECTORIO/cliente_sensor.csr" \
    -subj "/C=ES/ST=PaisVasco/L=Bilbao/O=Invernadero/CN=sensor_suelo_01"

openssl x509 -req -days $DIAS_VALIDEZ \
    -in "$DIRECTORIO/cliente_sensor.csr" \
    -CA "$DIRECTORIO/ca.crt" \
    -CAkey "$DIRECTORIO/ca.key" \
    -CAcreateserial \
    -out "$DIRECTORIO/cliente_sensor.crt"

echo " Cliente sensor creado: cliente_sensor.key + cliente_sensor.crt"


# Genera el certificado del CLIENTE 2, cerebro_datos/consumidor
echo "Creando certificado del CLIENTE 2, cerebro_datos"

openssl genrsa -out "$DIRECTORIO/cliente_cerebro.key" 2048

openssl req -new \
    -key "$DIRECTORIO/cliente_cerebro.key" \
    -out "$DIRECTORIO/cliente_cerebro.csr" \
    -subj "/C=ES/ST=PaisVasco/L=Bilbao/O=Invernadero/CN=cerebro_datos"

openssl x509 -req -days $DIAS_VALIDEZ \
    -in "$DIRECTORIO/cliente_cerebro.csr" \
    -CA "$DIRECTORIO/ca.crt" \
    -CAkey "$DIRECTORIO/ca.key" \
    -CAcreateserial \
    -out "$DIRECTORIO/cliente_cerebro.crt"

echo " Cliente cerebro creado: cliente_cerebro.key + cliente_cerebro.crt"


# Limpia los archivos temporales, los .csr.
rm -f "$DIRECTORIO"/*.csr "$DIRECTORIO"/*.srl

# Protegemos las claves privadas dándoles permisos restrictivos, solo lectura para el dueño
chmod 600 "$DIRECTORIO"/*.key