import base64
from ..config import Config
from ..rabbitmq import RabbitMQ

def fragment_to_json_queue(image_path):
    rabbitmq = RabbitMQ()
    # Читаем и кодируем изображение в Base64
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        rabbitmq.publish(base64_image)
    return True