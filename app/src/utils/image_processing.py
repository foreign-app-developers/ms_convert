import os
from ultralytics import YOLO
import cv2
from flask import current_app

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../yolo_models/best.pt")

# Функция обработки одного изображения
def process_image(image_path):
    fragments_folder = current_app.config['FRAGMENTS_FOLDER']
    model = YOLO(MODEL_PATH)
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
            if conf > 0.5:  # Если уверенность больше 0.7
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
        fragment_path = os.path.join(fragments_folder, f"{filename}_fragment_{i + 1}.jpg")
        cv2.imwrite(fragment_path, fragment)
        fragments.append(fragment_path)

    return fragments