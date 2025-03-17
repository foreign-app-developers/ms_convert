import pika
import time
import redis
import logging
import os
import json
import requests

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)  # уровень логирования инфо

# Подключение к Redis
redis_client = redis.Redis(host='redis_timer', port=6379, db=0)

# Подключение к RabbitMQ
connection_params = pika.URLParameters(f"amqp://admin:admin@xn--h1adbcol.xn----gtbbcb4bjf2ak.xn--p1ai:5672/%2f")
connection = pika.BlockingConnection(connection_params)
channel = connection.channel()

# Ограничение: обрабатываем по 1 запросу за раз
channel.basic_qos(prefetch_count=1)
channel.queue_declare(queue='rate_limit_queue', durable=True)

RATE_LIMIT = 15  # Максимум 15 запросов в минуту
WINDOW_SIZE = 60  # Окно в секундах

def request(base64_image):
    # API ключ для авторизации
    api_key = "AIzaSyAZlQp7T_qLyiAiWKJd37CcDubMx_AycvY"

    # URL для запроса
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    text = """
                    Ты – система, которая извлекает информацию из задания по английскому языку и преобразует её в строго структурированные данные в формате JSON. На вход подаётся изображение задания, содержащее текст с пропусками для заполнения. Твоя задача:
    1. Извлечь инструкцию (если она есть).
    2. Извлечь основной текст задания, при этом:
       - Удалить все числовые метки вида (1), (2), (3) и т.д.
       - Удалить любые подсказки или дополнительные пояснения, оставив только чистый текст.
       - На месте пропусков вставить метки [BLANK_1], [BLANK_2] и т.д.
    3. Сформировать массив объектов "blanks", где для каждого пропуска указаны:
       - **id**: числовой идентификатор пропуска.
       - **type**: тип пропуска (если пропуск, где есть выбор type = "multiple choise", если пропуск где есть подсказка, type = "clue", если просто пропуск и нет выбора и подсказок type = "empty").
       - **param**: дополнительный параметр (например, глагол в начальной форме или варианты ответа, разделённые знаком "/").

    Обратите внимание, что любая дополнительная информация (подсказки, варианты ответа, исходные числовые пометки) должна присутствовать только в массиве "blanks" и **не должна** выводиться в основном тексте.
    Если задания другого типа (не текст где нужно заполнить пропуски тогда верни только instruction, остальное оставь пустым)

    Возвращай только корректный JSON без каких-либо дополнительных комментариев. Пример ожидаемого формата:

    {
      "instruction": "fill gaps in text",
      "text": "Tony Hunt, a journalist, is interviewing Leila Markham, an environmental scientist. TONY: So tell me, Leila, why is it important to save the rainforests? LEILA: There are so many reasons. One reason is that lots of the plants which [BLANK_1] in the rainforest could be useful in medicine. We [BLANK_2] all the plants, but there are tens of thousands of them. ...",
      "blanks": [
        {"id": 1, "type": "clue", "param": "grow"},
        {"id": 2, "type": "clue", "param": "not/know"}
      ]
    }
                    """
    # Данные для запроса
    data = {
        "contents": [{
            "parts": [
                {"text": text},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64_image
                    }
                }
            ]
        }]
    }

    # Заголовки запроса
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        proxy_url = "http://45.186.6.104:3128"
        os.environ['http_proxy'] = proxy_url
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['https_proxy'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        # Отправляем POST запрос
        response = requests.post(url, headers=headers, data=json.dumps(data))
        logger.info(response)
        os.environ['http_proxy'] = ""
        os.environ['HTTP_PROXY'] = ""
        os.environ['https_proxy'] = ""
        os.environ['HTTPS_PROXY'] = ""
        # Загрузка строки в JSON-формат
        data = json.loads(response.text)

        # Извлечение текста JSON из строки, которая находится в 'text' объекта 'parts'
        json_text = data['candidates'][0]['content']['parts'][0]['text']

        # Преобразуем строку в настоящий JSON
        json_data = json.loads(json_text.strip('```json\n').strip())

        return json_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе{e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка{e}")

def get_wait_time():
    """Вычисляет, сколько ждать, если лимит превышен"""
    current_time = time.time()
    request_times = redis_client.lrange("request_times", 0, -1)

    if len(request_times) < RATE_LIMIT:
        return 0  # Можно отправлять сразу

    # Если лимит превышен — ждём до сброса самого старого запроса
    first_request_time = float(request_times[0])
    wait_time = (first_request_time + WINDOW_SIZE) - current_time
    return max(0, wait_time)

def log_request_time():
    """Логирует время запроса в Redis"""
    redis_client.rpush("request_times", time.time())
    redis_client.ltrim("request_times", -RATE_LIMIT, -1)  # Оставляем только последние 15

def callback(ch, method, properties, body):
    """Обработчик запросов (с Rate Limiting через Redis)"""
    request_data = body.decode()

    wait_time = get_wait_time()
    if wait_time > 0:
        logger.info(f"Rate limit exceeded! Sleeping for {wait_time:.2f} seconds")
        time.sleep(wait_time)

    # Отправка запроса на API
    response = request(request_data)
    logger.info(response)
    
    # Логируем запрос в Redis
    log_request_time()

    # Подтверждение обработки
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='rate_limit_queue', on_message_callback=callback)

logger.info("Queue is ready for messages...")
channel.start_consuming()