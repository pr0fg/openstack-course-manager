# OpenStack Course Manager  Copyright (C) 2020  Garrett Hayes

import os
from os.path import join, dirname

from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


class Config(object):

    # Global Configs
    DEBUG = True
    DISABLE_STUDENT_VM_SAVE = \
        True if os.getenv('DISABLE_STUDENT_VM_SAVE') == '1' \
        else False
    DISABLE_STUDENT_SNAPSHOTS = \
        True if os.getenv('DISABLE_STUDENT_SNAPSHOTS') == '1' \
        else False

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

    # Memcached for API tokens
    MEMCACHED_HOST = os.getenv('MEMCACHED_HOST')
    MEMCACHED_PORT = int(os.getenv('MEMCACHED_PORT'))

    # General Settings
    TIMEZONE = 'America/Toronto'
    SESSION_TIMEOUT = 3600

    # Email Backend
    EMAIL_DOMAINS = os.getenv('EMAIL_DOMAINS').split(',')
    EMAIL_SERVER = os.getenv('EMAIL_SERVER')
    EMAIL_PORT = os.getenv('EMAIL_PORT')
    EMAIL_USE_TLS = False if os.getenv('EMAIL_USE_TLS') == '0' else True
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    EMAIL_SENDER = os.getenv('EMAIL_SENDER')

    # Links for Automated Emails
    CLOUD_URL = os.getenv('CLOUD_URL')
    COURSE_MANAGER_URL = os.getenv('COURSE_MANAGER_URL')
    VPN_CLIENT_URL = os.getenv('VPN_CLIENT_URL')
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
                'networks': 10
            }
        }
    }
