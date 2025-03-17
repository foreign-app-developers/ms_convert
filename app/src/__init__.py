from flask import Flask
from .config import Config
from flasgger import Swagger
import os
import pika

def create_app():
    app = Flask(__name__)
    app.config
    app.config.from_object(Config)

    # Создание папок, если их нет
    for folder in [app.config["UPLOAD_FOLDER"], app.config["IMAGES_FOLDER"], app.config["FRAGMENTS_FOLDER"]]:
        os.makedirs(folder, exist_ok=True)

    # Инициализация Swagger
    Swagger(app)

    # Регистрация Blueprint'ов
    import src.routes  # Абсолютный импорт из src
    app.register_blueprint(src.routes.bp_converter)

    return app