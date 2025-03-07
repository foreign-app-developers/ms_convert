import base64
import json
import pymupdf
import requests
import cv2
from ultralytics import YOLO
import os
from flask import Flask, request, jsonify
import time
from flasgger import Swagger
import socket
import gunicorn

app = Flask(__name__)

MAX_REQUESTS_COUNT_PER_MIN = 15
requests_count = 0
requests_ft = 0

UPLOAD_FOLDER = "./uploads"
IMAGES_FOLDER = "./images"
FRAGMENTS_FOLDER = "./fragments"

app.config['upload_folder'] = UPLOAD_FOLDER
app.config['SWAGGER'] = {
    'title': 'PDF/PNG/JPG to Json API',
    'specs_route': '/doc'  # документация будет доступна по маршруту /doc
}
swagger = Swagger(app)

# Кастомное исключение для превышения лимита запросов
class TooManyRequestsError(Exception):
    pass


# Подсчёт кол-ва запросов в минуту
def increment_requests_count():
    global requests_ft
    global requests_count
    if requests_count == 0:
        requests_ft = time.time()
    if requests_count > MAX_REQUESTS_COUNT_PER_MIN - 1:
        now = time.time()
        if now - requests_ft < 60:
            raise TooManyRequestsError("too many requests")
        else:
            requests_ft = time.time()
            requests_count = 0
    requests_count += 1
    return True


# Функция обработки одного изображения
def process_image(image_path):
    model = YOLO("best.pt")
    fragments = []

    # Загружаем изображение
    image = cv2.imread(image_path)
    results = model(image)

    # Список для хранения отфильтрованных объектов
    filtered_results = []

    # Проходим по результатам модели
    for result in results:
        # Для каждого объекта в результате
        filtered_boxes = []
        for box in result.boxes:
            conf = box.conf[0].item()  # Уверенность объекта
            if conf > 0.7:  # Если уверенность больше 0.7
                filtered_boxes.append(box)

        # Добавляем отфильтрованные объекты в новый результат
        if filtered_boxes:
            result.boxes = filtered_boxes
            filtered_results.append(result)

    # Список верхних координат объектов "task"
    task_y_coords = [int(box.xyxy[0][1].item()) for result in filtered_results for box in result.boxes]

    # Если объектов нет, пропускаем изображение
    if not task_y_coords:
        print(f"Объекты 'task' не найдены: {image_path}")
        return

    # Сортируем границы по Y (сверху вниз)
    task_y_coords.sort()

    # Разрезаем изображение на фрагменты
    filename = os.path.splitext(os.path.basename(image_path))[0]  # Имя файла без расширения
    for i in range(len(task_y_coords)):
        if i == len(task_y_coords) - 1:
            fragment = image[task_y_coords[i]:, :]  # Последний фрагмент до конца

        else:
            y1, y2 = task_y_coords[i], task_y_coords[i + 1]
            fragment = image[y1:y2, :]  # Вырезаем область от y1 до y2

        # Путь для сохранения
        fragment_path = os.path.join(FRAGMENTS_FOLDER, f"{filename}_fragment_{i + 1}.jpg")
        cv2.imwrite(fragment_path, fragment)
        fragments.append(fragment_path)

    return fragments


def extract_images_from_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)
    image_paths = []

    for page_num in range(len(doc)):
        # Получаем изображение страницы (pixmap)
        page = doc.load_page(page_num)

        matrix = pymupdf.Matrix(3, 3)  # zoom определяет уровень масштабирования

        # Конвертируем страницу в пиксмап (изображение) с высоким разрешением
        pix = page.get_pixmap(matrix=matrix)

        # Сохраняем изображение как PNG
        img_path = os.path.join(IMAGES_FOLDER, f"page_{page_num + 1}.png")
        pix.save(img_path)
        image_paths.append(img_path)

    return image_paths


@app.route("/")
def check_worker():
    return f"Container ID: {socket.gethostname()}"

@app.route("/process_png", methods=["POST"])
def process_png():
    """
    ---
    parameters:
       - name: "file"
         in: "formData"
         description: "PNG file to be processed"
         required: true
         type: "file"
    responses:
        200:
          description: "Success - Returns a JSON response with tasks"
          examples:
            application/json:
              message: "success"
              tasks:
                - instruction: "fill gaps in text"
                  text: "Tony Hunt, a journalist, is interviewing Leila Markham, an environmental scientist. ..."
                  blanks:
                    - id: 1
                      type: "clue"
                      param: "grow"
        400:
          description: "Bad Request - possible errors"
          examples:
            application/json:
              error1: "File not found"
              error2: "Wrong file format"
    """
    if "file" not in request.files:
        return jsonify({"error": "File not found"}), 400
    png_file = request.files['file']
    png_name = png_file.filename
    file_extension = os.path.splitext(png_name)[1].lower()
    if file_extension != "png" or "jpg":
        return jsonify({"error" : "Wrong file format"}),400
    png_path = os.path.join(UPLOAD_FOLDER, png_name)
    png_file.save(png_path)
    dictionaries = []
    image_fragments = process_image(png_path)

    # удаляем изначальную картинку
    os.remove(png_path)

    if image_fragments:  # Проверяем, не пуст ли список
        for image_fragment in image_fragments:
            tmp_dict = fragment_to_json(image_fragment)
            if tmp_dict:
                dictionaries.append(tmp_dict)

    clear_fragments(image_fragments)

    return jsonify({"message": "success", "tasks": dictionaries})


@app.route("/process_pdf", methods=["POST"])
def process_pdf():
    if "file" not in request.files:
        return jsonify({"error": "File not found"}), 400
    pdf_file = request.files['file']
    pdf_name = pdf_file.filename
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_name)
    pdf_file.save(pdf_path)

    # Извлечение изображений из PDF
    image_paths = extract_images_from_pdf(pdf_path)
    if not image_paths:
        return jsonify({"error": "Failed to extract images"}), 400

    # Обработка изображений
    dictionaries = []
    for image_path in image_paths:
        image_fragments = process_image(image_path)  # Получаем фрагменты для изображения
        if image_fragments:  # Проверяем, не пуст ли список
            for image_fragment in image_fragments:
                try:
                    increment_requests_count()
                except TooManyRequestsError as e:
                    return jsonify({"message": "too many requests", "tasks": dictionaries})
                tmp_dict = fragment_to_json(image_fragment)
                if tmp_dict:
                    dictionaries.append(tmp_dict)

    return jsonify({"message": "success", "tasks": dictionaries})


def clear_fragments(fragments_paths):
    for fragments_path in fragments_paths:
        os.remove(fragments_path)


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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
