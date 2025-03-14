import time
from flask import current_app
# Кастомное исключение для превышения лимита запросов
class TooManyRequestsError(Exception):
    pass

# Подсчёт кол-ва запросов в минуту
def increment_requests_count():
    max_req = current_app.config['MAX_REQUESTS_COUNT_PER_MIN']
    global requests_ft
    global requests_count
    if requests_count == 0:
        requests_ft = time.time()
    if requests_count > max_req - 1:
        now = time.time()
        if now - requests_ft < 60:
            raise TooManyRequestsError("too many requests")
        else:
            requests_ft = time.time()
            requests_count = 0
    requests_count += 1
    return True