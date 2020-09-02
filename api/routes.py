# OpenStack Course Manager API Copyright (C) 2020  Garrett Hayes

import random
import string

from flask import request, send_from_directory
from flask_restful import Resource, abort, wraps, reqparse
from expiring_dict import ExpiringDict
from celery.utils.log import get_task_logger

from api import app, api, celery
from manager import OpenStackCourseManager
from config import Config

manager = OpenStackCourseManager(debug=Config.DEBUG)
sessions = ExpiringDict(Config.SESSION_TIMEOUT)
logger = get_task_logger(__name__)


# -----------------------------------------------------------------------------
# Celery Task Wrapper

@celery.task
def celery_wrapper(function_name, *args, **kwargs):
    logger.info(f'Received task name: {function_name}')
    method_to_call = getattr(manager, function_name)
    return {'result': method_to_call(*args, **kwargs)}


# -----------------------------------------------------------------------------
# Decorators

def requires_token(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        token = request.cookies.get('oscm')
        course_code = verify_token(token)

        if not course_code:
            abort(401, message='Invalid token')

        return func(*args, **kwargs, course_code=course_code, token=token)

    return decorated


def requires_cron_token(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        if not request.cookies.get('OSCM_TOKEN') == Config.CRON_TOKEN:
            abort(401, message='Invalid cron token')

        return func(*args, **kwargs)

    return decorated


# -----------------------------------------------------------------------------
# Return Messages

def parse_result(result):
    if result:
        return {'result': 'ok'}
    else:
        abort(400, message='Invalid request')


def task_queued():
    return {'result': 'task queued'}


# -----------------------------------------------------------------------------
# Authentication Methods

def get_token(course_code):
    token = ''.join(random.choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits)
        for _ in range(64))
    sessions[token] = course_code
    return token


def verify_token(token):
    if token in sessions.keys():
        return sessions[token]
    else:
        return False


def revoke_token(token):
    sessions.pop(token, None)
    return True


# -----------------------------------------------------------------------------
# API Views


class CheckToken(Resource):

    @requires_token
    def get(self, **kwargs):
        return {'course': kwargs.get('course_code')}


class Login(Resource):

    def post(self):

        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True)
        parser.add_argument('password', type=str, required=True)
        parser.add_argument('course_code', type=str, required=True)
        args = parser.parse_args()

        login_success = manager.login(check_credentials=True,
                                      course_code=args['course_code'],
                                      username=args['username'],
                                      password=args['password'])

        if login_success:
            return {'token': {
                'name': 'oscm',
                'value': get_token(args['course_code']),
                'expires': Config.SESSION_TIMEOUT}
            }
        else:
            abort(401, message='Login failed')


class Logout(Resource):

    @requires_token
    def get(self, **kwargs):
        return parse_result(revoke_token(kwargs.get('token')))


class PasswordReset(Resource):

    @requires_token
    def get(self, username, **kwargs):
        celery_wrapper.delay('set_password',
                             kwargs.get('course_code'),
                             username)
        return task_queued()


class Settings(Resource):

    @requires_token
    def get(self, **kwargs):
        return manager.get_settings(kwargs.get('course_code'))

    @requires_token
    def patch(self, **kwargs):
        data = request.get_json()
        return parse_result(
            manager.set(kwargs.get('course_code'), **data))


class Stats(Resource):

    @requires_token
    def get(self, **kwargs):

        users = manager.get_users(kwargs.get('course_code'),
                                  students=True, groups=True, instructors=True)
        return {
            'students': len(users['students']),
            'groups': len(users['groups']),
            'instructors': len(users['instructors'])
        }


class Schedule(Resource):

    @requires_token
    def get(self, **kwargs):
        return manager.get_settings(kwargs.get('course_code'))['schedule']

    @requires_token
    def post(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('day', type=int, required=True)
        parser.add_argument('start_hour', type=int, required=True)
        parser.add_argument('start_minute', type=int, required=True)
        parser.add_argument('end_hour', type=int, required=True)
        parser.add_argument('end_minute', type=int, required=True)
        args = parser.parse_args()

        return parse_result(
            manager.add_schedule(kwargs.get('course_code'),
                                 args['day'],
                                 args['start_hour'],
                                 args['start_minute'],
                                 args['end_hour'],
                                 args['end_minute']))

    @requires_token
    def delete(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('day', type=int, required=True)
        parser.add_argument('start_hour', type=int, required=True)
        parser.add_argument('start_minute', type=int, required=True)
        parser.add_argument('end_hour', type=int, required=True)
        parser.add_argument('end_minute', type=int, required=True)
        args = parser.parse_args()

        return parse_result(
            manager.remove_schedule(kwargs.get('course_code'),
                                    args['day'],
                                    args['start_hour'],
                                    args['start_minute'],
                                    args['end_hour'],
                                    args['end_minute']))


class Quota(Resource):

    @requires_token
    def get(self, **kwargs):
        return manager.get_settings(kwargs.get('course_code'))['quota']

    @requires_token
    def patch(self, **kwargs):
        data = request.get_json()
        return parse_result(
            manager.set(kwargs.get('course_code'), quota=data))


class Instructors(Resource):

    @requires_token
    def get(self, **kwargs):
        return manager.get_users(kwargs.get('course_code'),
                                 instructors=True,
                                 details=True)['instructors']

    @requires_token
    def post(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True)
        parser.add_argument('email', type=str, required=True)
        args = parser.parse_args()

        return parse_result(manager.add_user(
            kwargs.get('course_code'),
            args['username'],
            args['email'],
            instructor=True))

    @requires_token
    def delete(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True)
        args = parser.parse_args()

        return parse_result(manager.remove_user(
            kwargs.get('course_code'), args['username'], instructor=True))


class Students(Resource):

    @requires_token
    def get(self, **kwargs):
        return manager.get_users(kwargs.get('course_code'),
                                 students=True,
                                 details=True)['students']

    @requires_token
    def post(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True)
        parser.add_argument('email', type=str, required=True)
        args = parser.parse_args()

        celery_wrapper.delay('add_user',
                             kwargs.get('course_code'),
                             args['username'],
                             args['email'])
        return task_queued()

    @requires_token
    def delete(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True)
        args = parser.parse_args()

        return parse_result(manager.remove_user(
            kwargs.get('course_code'), args['username']))


class Groups(Resource):

    @requires_token
    def get(self, **kwargs):
        return manager.get_users(kwargs.get('course_code'),
                                 groups=True, details=True)['groups']

    @requires_token
    def post(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True)
        parser.add_argument('group_number', type=int, required=True)
        args = parser.parse_args()

        celery_wrapper.delay('add_student_to_group',
                             kwargs.get('course_code'),
                             args['username'],
                             args['group_number'])

        return task_queued()

    @requires_token
    def delete(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True)
        parser.add_argument('group_number', type=int, required=True)
        args = parser.parse_args()

        return parse_result(manager.remove_user(
            kwargs.get('course_code'),
            args['username'],
            args['group_number']))


class Images(Resource):

    @requires_token
    def get(self, **kwargs):
        return manager.get_images(kwargs.get('course_code'),
                                  instructor_only=True)

    @requires_token
    def patch(self, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('image', type=str, required=True)
        parser.add_argument('shared', type=bool, required=True)
        args = parser.parse_args()

        celery_wrapper.delay(
            'share_image' if args['shared'] else 'unshare_image',
            kwargs.get('course_code'),
            args['image'])

        return task_queued()


class Cron(Resource):

    @requires_cron_token
    def get(self, **kwargs):

        for course_code in manager.courses:

            is_running = manager.is_running(course_code)

            if is_running:
                celery_wrapper.delay(
                    'set_access',
                    course_code,
                    students=True,
                    groups=True,
                    enabled=True)

            else:
                celery_wrapper.delay('remove_student_vms', course_code)
                celery_wrapper.delay('shelve_vms', course_code)
                celery_wrapper.delay('set_access', course_code, students=True,
                                     groups=True, enabled=False)

        return task_queued()


# Endpoints
api.add_resource(CheckToken, '/api/token')
api.add_resource(Login, '/api/login')
api.add_resource(Logout, '/api/logout')
api.add_resource(PasswordReset, '/api/users/<string:username>/reset')
api.add_resource(Settings, '/api/settings')
api.add_resource(Stats, '/api/stats')
api.add_resource(Schedule, '/api/schedule')
api.add_resource(Quota, '/api/quota')
api.add_resource(Instructors, '/api/instructors')
api.add_resource(Students, '/api/students')
api.add_resource(Groups, '/api/groups')
api.add_resource(Images, '/api/images')
api.add_resource(Cron, '/api/cron')


# For debugging or development purposes only!
if Config.DEBUG and Config.WWW_PATH:
    @app.route('/<path:filename>')
    def serve_static(filename):
        return send_from_directory(Config.WWW_PATH, filename)