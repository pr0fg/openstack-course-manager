# OpenStack Course Manager  Copyright (C) 2020  Garrett Hayes

import os
import string
import random
from os.path import join, dirname

from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


class Config(object):

    DEBUG = True if os.getenv('DEBUG') == '1' else False

    # OpenStack Additional Requirements
    OS_DOMAIN_ID = os.getenv('OS_DOMAIN_ID')
    OS_USER_ROLE_ID = os.getenv('OS_USER_ROLE_ID')

    # Optional for Pytest and development
    OS_TEST_IMAGE_ID = os.getenv('OS_TEST_IMAGE_ID')
    OS_TEST_IMAGE_FLAVOR_ID = os.getenv('OS_TEST_IMAGE_FLAVOR_ID')
    WWW_PATH = os.getenv('WWW_PATH')

    # Celery Details for Worker
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
    CELERY_BACKEND_URL = os.getenv('CELERY_BACKEND_URL')

    # General Settings
    CRON_TOKEN = ''.join(random.choice(
                 string.ascii_uppercase+string.ascii_lowercase+string.digits)
                 for _ in range(64))

    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT')) \
        if os.getenv('SESSION_TIMEOUT') else 3600

    # Email Backend
    EMAIL_DOMAINS = os.getenv('EMAIL_DOMAINS').split(',')
    EMAIL_SERVER = os.getenv('EMAIL_SERVER')
    EMAIL_PORT = os.getenv('EMAIL_PORT')
    EMAIL_USE_TLS = False if os.getenv('EMAIL_USE_TLS') == '0' else True
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    EMAIL_SENDER = os.getenv('EMAIL_SENDER')

    # Links for Automated Emails
    CLOUD_URL = os.getenv('EMAIL_SERVER')
    COURSE_MANAGER_URL = os.getenv('EMAIL_SERVER')
    VPN_FILE_URL = os.getenv('VPN_FILE_URL')
    VPN_SETUP_GUIDE = os.getenv('VPN_SETUP_GUIDE')

    # Course Setting Defaults
    DEFAULT_COURSE_SETTINGS = {
        'keep': False,
        'weekend': True,
        'snapshots': False,
        'schedule': {},
        'quota': {
            'students': {
                'instances': 2,
                'cores': 2,
                'ram': 4096,
                'networks': 0
            },
            'groups': {
                'instances': 5,
                'cores': 5,
                'ram': 10240,
                'networks': 5
            }
        }
    }
