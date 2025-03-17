from flask import current_app
import pymupdf

def extract_images_from_pdf(pdf_path):
    images_folder = current_app.config['IMAGES_FOLDER']
    doc = pymupdf.open(pdf_path)
    image_paths = []

    for page_num in range(len(doc)):
        # Получаем изображение страницы (pixmap)
        page = doc.load_page(page_num)

        matrix = pymupdf.Matrix(3, 3)  # zoom определяет уровень масштабирования

        # Конвертируем страницу в пиксмап (изображение) с высоким разрешением
        pix = page.get_pixmap(matrix=matrix)

        # Сохраняем изображение как PNG
        img_path = os.path.join(images_folder, f"page_{page_num + 1}.png")
        pix.save(img_path)
        image_paths.append(img_path)

    return image_paths