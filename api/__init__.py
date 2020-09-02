# OpenStack Course Manager API Copyright (C) 2020  Garrett Hayes

from flask import Flask
from flask_restful import Api
from celery import Celery

from config import Config


app = Flask(__name__)
api = Api(app)

if Config.DEBUG:
    print(f'Cron Token: {Config.CRON_TOKEN}')

celery = Celery('oscm', broker=Config.CELERY_BROKER_URL,
                backend=Config.CELERY_BACKEND_URL)

from api import routes
