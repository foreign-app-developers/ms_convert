import pika
from pika.exceptions import AMQPConnectionError
import logging
import time
from .config import Config

logger = logging.getLogger(__name__)

class RabbitMQ:
    def __init__(self):
        self.max_retries = 5
        self.delay = 1  # Начальная задержка в секундах
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        retries = 0
        delay = self.delay

        while retries < self.max_retries:
            try:
                connection_params = pika.URLParameters(Config.RABBITMQ)
                self.connection = pika.BlockingConnection(connection_params)
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue='rate_limit_queue', durable=True)
                return True
            except AMQPConnectionError as e:
                logger.warning(f"Connection failed (attempt {retries + 1}/{self.max_retries}): {e}")
                retries += 1
                time.sleep(delay)
                delay *= 2 

        raise Exception(f"Could not connect to RabbitMQ after {self.max_retries} retries")

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ connection closed")
    
    def publish(self, image):
        self.channel.basic_publish(
        exchange='',
        routing_key='rate_limit_queue',
        body=image,
        properties=pika.BasicProperties(
            delivery_mode=2  # Персистентность сообщений
        )
    )
