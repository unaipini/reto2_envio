# Define las instrucciones para construir el contenedor docker productor
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulador_sensor.py .

CMD ["python", "simulador_sensor.py"]