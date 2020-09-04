# OpenStack Course Manager API Copyright (C) 2020  Garrett Hayes

import random
import string

from flask import request, redirect
from flask_restful import Resource, abort, wraps, reqparse
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from expiring_dict import ExpiringDict

from api import api, celery
from manager import OpenStackCourseManager
from config import Config

manager = OpenStackCourseManager(debug=Config.DEBUG)
sessions = ExpiringDict(Config.SESSION_TIMEOUT)
reset_tokens = ExpiringDict(Config.SESSION_TIMEOUT)
logger = get_task_logger(__name__)


# -----------------------------------------------------------------------------
# Celery Task Wrapper

@celery.task
def celery_wrapper(function_name, *args, **kwargs):
    logger.info(f'Received task name: {function_name}')
    method_to_call = getattr(manager, function_name)
    return method_to_call(*args, **kwargs)


# -----------------------------------------------------------------------------
# Celery Periodic Tasks

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    sender.add_periodic_task(
        crontab(hour='*', minute='*/10', day_of_week='*'),
        cron_enforce_acl_policy.s(),
        name='Enforce ACL Policies'
    )

    sender.add_periodic_task(
        crontab(hour=1, minute=0, day_of_week='*'),
        cron_enforce_quota_policy.s(),
        name='Enforce Quota Policies'
    )

    sender.add_periodic_task(
        crontab(hour=2, minute=0, day_of_week='*'),
        cron_student_vm_reaper.s(),
        name='Student VM Reaper'
    )

    sender.add_periodic_task(
        crontab(hour=3, minute=0, day_of_week='*'),
        cron_student_snapshot_reaper.s(),
        name='Student Snapshot Reaper'
    )


@celery.task
def cron_enforce_acl_policy():
    for course_code in manager.courses:
        is_running = manager.is_running(course_code)
        manager.set_access(course_code, students=True, groups=True,
                           enabled=is_running)


@celery.task
def cron_enforce_quota_policy():
    for course_code in manager.courses:
        manager.set_quota(course_code, students=True, groups=True)


@celery.task
def cron_student_vm_reaper():
    for course_code in manager.courses:
        manager.remove_student_vms(course_code)


@celery.task
def cron_student_snapshot_reaper():
    for course_code in manager.courses:
        manager.remove_student_snapshots(course_code)


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

def get_token(course_code=None):
    token = ''.join(random.choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits)
        for _ in range(64))
    if course_code:
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
# Public API Views


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


class PasswordResetRequest(Resource):

    def get(self, course_code, username):

        course_users = manager.get_users(course_code, instructors=True,
                                         students=True)
        if course_users and (
                username in course_users['instructors'] or
                username in course_users['students']):

            token = get_token()
            reset_tokens[token] = [course_code, username]
            manager.send_password_reset_request_email(
                course_code, username, token)

        return parse_result(True)


class PasswordResetConfirm(Resource):

    def get(self, token):

        if token not in reset_tokens.keys():
            return redirect(Config.CLOUD_URL, code=302)

        else:
            course_code = reset_tokens[token][0]
            username = reset_tokens[token][1]
            del reset_tokens[token]
            manager.set_password(course_code, username)
            return redirect(Config.CLOUD_URL, code=302)


# -----------------------------------------------------------------------------
# Authenticated API Views

class Logout(Resource):

    @requires_token
    def get(self, **kwargs):
        return parse_result(revoke_token(kwargs.get('token')))


class PasswordReset(Resource):

    @requires_token
    def get(self, username, **kwargs):
        return parse_result(
            manager.set_password(kwargs.get('course_code'), username))


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


# Public Endpoints
api.add_resource(CheckToken, '/public/token')
api.add_resource(Login, '/public/login')
api.add_resource(
    PasswordResetRequest,
    '/public/reset/<string:course_code>/<string:username>')
api.add_resource(
    PasswordResetConfirm,
    '/public/reset/<string:token>')

# Authenticated Endpoints
api.add_resource(Logout, '/logout')
api.add_resource(PasswordReset, '/users/<string:username>/reset')
api.add_resource(Settings, '/settings')
api.add_resource(Stats, '/stats')
api.add_resource(Schedule, '/schedule')
api.add_resource(Quota, '/quota')
api.add_resource(Instructors, '/instructors')
api.add_resource(Students, '/students')
api.add_resource(Groups, '/groups')
api.add_resource(Images, '/images')


# For debugging or development purposes only!
# if Config.DEBUG and Config.WWW_PATH:
#     @app.route('/<path:filename>')
#     def serve_static(filename):
#         return send_from_directory(Config.WWW_PATH, filename)
