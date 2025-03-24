from flask import request, jsonify, Blueprint, current_app
from ..utils.image_processing import process_image
from ..utils.pdf_processing import extract_images_from_pdf
from ..utils.request_limit import increment_requests_count, TooManyRequestsError
from ..utils.google_api import fragment_to_json
import os
import socket

bp_converter = Blueprint('converter', __name__, url_prefix='/converter')

@bp_converter.route("/")
def check_worker():
    return f"Container ID: {socket.gethostname()}"

@bp_converter.route("/process_png", methods=["POST"])
def process_png():
    """
    Метод принимает изображение с одним заданием или с целой страницей из учебника. Протестировано на учебнике:https://online.flipbuilder.com/chfvo/puhv/
    ---
    parameters:
       - name: "file"
         in: "formData"
         description: "PNG or JPG file to be processed"
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

    # Check for valid file format (png or jpg)
    if file_extension not in [".png", ".jpg"]:
        return jsonify({"error": "Wrong file format"}), 400
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    png_path = os.path.join(upload_folder, png_name)
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
        for image_fragment in image_fragments: # удаляем фрагменты
            os.remove(image_fragment)
    else: return jsonify({"error": "No tasks found"}), 400


    return jsonify({"message": "success", "tasks": dictionaries})

# @bp_converter.route("/process_pdf", methods=["POST"])
# def process_pdf():
#     if "file" not in request.files:
#         return jsonify({"error": "File not found"}), 400
#     pdf_file = request.files['file']
#     pdf_name = pdf_file.filename
#     upload_folder = current_app.config["UPLOAD_FOLDER"]
#     pdf_path = os.path.join(upload_folder, pdf_name)
#     pdf_file.save(pdf_path)

#     # Извлечение изображений из PDF
#     image_paths = extract_images_from_pdf(pdf_path)
#     if not image_paths:
#         return jsonify({"error": "Failed to extract images"}), 400

#     # Обработка изображений
#     dictionaries = []
#     for image_path in image_paths:
#         image_fragments = process_image(image_path)  # Получаем фрагменты для изображения
#         if image_fragments:  # Проверяем, не пуст ли список
#             for image_fragment in image_fragments:
#                 try:
#                     increment_requests_count()
#                 except TooManyRequestsError as e:
#                     return jsonify({"message": "too many requests", "tasks": dictionaries})
#                 tmp_dict = fragment_to_json(image_fragment)
#                 if tmp_dict:
#                     dictionaries.append(tmp_dict)

#     return jsonify({"message": "success", "tasks": dictionaries})
