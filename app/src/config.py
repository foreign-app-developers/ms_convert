class Config:
    MAX_REQUESTS_COUNT_PER_MIN = 15
    requests_count = 0
    requests_ft = 0
    SWAGGER = {
        'title': 'PDF/PNG/JPG to Json API',
        'specs_route': '/converter/doc',
        'static_url_path': '/flasgger_static'
    }
    UPLOAD_FOLDER = "./uploads"
    IMAGES_FOLDER = "./images"
    FRAGMENTS_FOLDER = "./fragments"
    RABBITMQ = "amqp://admin:admin@xn--h1adbcol.xn----gtbbcb4bjf2ak.xn--p1ai:5672/%2f"