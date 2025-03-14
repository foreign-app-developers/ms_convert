FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 && \
    pip install --no-cache-dir -r requirements.txt

# Копируем run.py и папку src
COPY run.py .
COPY src/ ./src/

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]