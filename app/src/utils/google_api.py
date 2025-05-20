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
Ты – система для извлечения информации из задания по английскому языку и преобразования её в строго структурированные данные в формате JSON.

На вход подаётся изображение задания, содержащее текст с пропусками. Выполни следующие шаги:

1. **Извлеки инструкцию**, если она есть. Сохрани как строку в поле `"instruction"`.

2. **Извлеки основной текст задания** и обработай его:
   - Удали числовые метки вида (1), (2), (3) и т.д.
   - Удали подсказки и пояснения — основной текст должен быть "чистым".
   - На месте каждого пропуска вставь метку `[BLANK_N]`, где `N` — порядковый номер (начиная с 1).

3. Создай массив объектов `"blanks"`, по одному на каждый пропуск. Для каждого:
   - `id`: номер пропуска (целое число, начиная с 1).
   - `type`: тип пропуска:
     - `"multiple choice"` — если есть варианты ответа. Однако если слова нужно как-то ещё преобразовать то это НЕ multiple choice, а clue, а варианты ответа уйдут в param.
     - `"clue"` — если есть подсказка.
     - `"empty"` — если просто пропуск.
     - в одном задании типы всех пропусков одинаковые.
   - `param`: строка с данными:
     - если `"multiple choice"` — перечисли варианты через `/` (например, `"is/are/was"`),
     - если `"clue"` — укажи подсказку (например, начальная форма глагола),
     - если `"empty"` — оставь пустую строку `""`.

4. Если задание **не содержит пропусков для заполнения**, просто верни `"instruction"` и `"text"`, а `"blanks"` оставь пустым массивом.

**Важно:** Вся дополнительная информация (подсказки, варианты, номера) должна быть только в массиве `"blanks"` и не присутствовать в основном тексте `"text"`.

Возвращай только **валидный JSON** без комментариев и пояснений.

**Пример ожидаемого результата:**

```json
{
  "instruction": "Fill in the blanks with the correct form of the verbs.",
  "text": "Tony Hunt, a journalist, is interviewing Leila Markham, an environmental scientist. TONY: So tell me, Leila, why is it important to save the rainforests? LEILA: There are so many reasons. One reason is that lots of the plants which [BLANK_1] in the rainforest could be useful in medicine. We [BLANK_2] all the plants, but there are tens of thousands of them.",
  "blanks": [
    { "id": 1, "type": "clue", "param": "grow" },
    { "id": 2, "type": "clue", "param": "not/know" }
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
            proxy_url = "http://45.140.143.77:18080"
            os.environ['http_proxy'] = proxy_url
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['https_proxy'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            # Отправляем POST запрос
            response = requests.post(url, headers=headers, data=json.dumps(data))
            print(response.text,flush=True)
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
