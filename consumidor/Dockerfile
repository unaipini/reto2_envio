# Define las instrucciones para construir el contenedor docker consumidor
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY guardar_datos.py .

CMD ["python", "guardar_datos.py"]