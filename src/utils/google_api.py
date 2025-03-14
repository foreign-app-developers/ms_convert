import os
import json
import time
import requests
import base64

def fragment_to_json(image_path):
    # API ключ для авторизации
    api_key = "AIzaSyAZlQp7T_qLyiAiWKJd37CcDubMx_AycvY"

    # URL для запроса
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    # Читаем и кодируем изображение в Base64
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
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

    for attempt in range(2):
        try:
            proxy_url = "http://45.186.6.104:3128"
            os.environ['http_proxy'] = proxy_url
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['https_proxy'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            # Отправляем POST запрос
            response = requests.post(url, headers=headers, data=json.dumps(data))
            os.environ['http_proxy'] = ""
            os.environ['HTTP_PROXY'] = ""
            os.environ['https_proxy'] = ""
            os.environ['HTTPS_PROXY'] = ""
            time.sleep(1)
            # Загрузка строки в JSON-формат
            data = json.loads(response.text)

            # Извлечение текста JSON из строки, которая находится в 'text' объекта 'parts'
            json_text = data['candidates'][0]['content']['parts'][0]['text']

            # Преобразуем строку в настоящий JSON
            json_data = json.loads(json_text.strip('```json\n').strip())

            return json_data
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе (попытка {attempt + 1}/{2}): {e}")
        except Exception as e:
            print("Непредвиденная ошибка")

        # Если все попытки не удались
    print("Не удалось получить данные после нескольких попыток.")
    return None