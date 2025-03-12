FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y libgl1-mesa-glx && apt-get install -y libglib2.0-0 && \
    pip install -r requirements.txt

CMD gunicorn --bind 0.0.0.0:5000 api_google_gemini:app

