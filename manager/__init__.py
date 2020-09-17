#!/usr/bin/env python

# OpenStack Course Manager  Copyright (C) 2020  Garrett Hayes

import random
import string
import json
import os
import logging
import smtplib
import ssl
from datetime import time, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr

import openstack

from config import Config

current_dir = os.path.dirname(__file__)


class OpenStackCourseManager():

    def __init__(self, debug=False):

        logging.basicConfig(level=logging.DEBUG if (debug or Config.DEBUG)
                            else logging.INFO,
                            format=f'%(levelname)s: %(message)s')

        openstack.enable_logging(
            debug=True if bool(os.getenv('OS_DEBUG')) else False)

        logging.info('Connecting to cloud')
        self._cloud, self._admin_project = self.login()
        self._admin_user = self._get_user(os.getenv('OS_USERNAME'))
        logging.info(f'Ready')

    # ------------------------------------------------------------------------
    @property
    def courses(self):
        return ['-'.join(project.name.split('-')[0:2])
                for project in self._cloud.identity.projects()
                if 'Instructors' in project.name]

    # ------------------------------------------------------------------------
    # Decorators

    def requires_course_code(func):

        def decorated(self, *args, **kwargs):

            course_code = str(args[0])

            course_project = self._get_project(
                course_code,
                f'{course_code}-Instructors'
            )

            if not course_project:
                logging.info(f'Course does not exist: {course_code}')
                return False

            return func(self, *args, **kwargs, course_project=course_project)

        return decorated

    def requires_student(func):

        def wrapper_requires_student(self, *args, **kwargs):

            course_code = str(args[0])
            username = str(args[1])

            user = self._get_user(username)
            if not user or not user.is_enabled:
                return False

            project = self._get_project(
                course_code,
                f'{course_code}-{username}'
            )

            if not project:
                logging.error(f'{course_code}: \
                    {username} not student in course')
                return False

            return func(self, *args, **kwargs, user=user, project=project)

        return wrapper_requires_student

    def requires_instructor_or_student(func):

        def wrapper_requires_instructor_or_student(self, *args, **kwargs):

            course_code = str(args[0])
            username = str(args[1])

            user = self._get_user(username)
            if not user or not user.is_enabled:
                return False

            project = self._get_project(
                course_code,
                f'{course_code}-{username}'
            )

            if not project:

                for u in self._cloud.identity.role_assignments(
                     scope_project_id=kwargs.get('course_project').id,
                     role_id=Config.OS_USER_ROLE_ID):

                    if u.user['id'] == user.id:
                        project = kwargs.get('course_project')

                if not project:
                    logging.error(f'{course_code}: \
                        {username} not in course')
                    return False

            return func(self, *args, **kwargs, user=user, project=project)

        return wrapper_requires_instructor_or_student

    def requires_image_in_course(func):

        def wrapper_requires_image_in_course(self, *args, **kwargs):

            image_id = str(args[1])

            image = self._get_image(str(image_id))
            if not image:
                return False

            if not image.owner == kwargs.get('course_project').id:
                logging.info(f'{kwargs.get("course_code")}: \
                    Image {image.name} not in course')
                return False

            return func(self, *args, **kwargs, image=image)

        return wrapper_requires_image_in_course

    # ------------------------------------------------------------------------
    def login(self, check_credentials=False, course_code=None, username=None,
              password=None):

        if check_credentials:
            cloud = openstack.connect(
                cloud='envvars',
                username=username,
                password=password,
                project_name=f'{course_code}-Instructors')
        else:
            cloud = openstack.connect(cloud='envvars')

        logging.debug(f'Cloud connection established')

        try:
            cloud.authorize()
            logging.info(f'Login successful for \
                {username if username else os.getenv("OS_USERNAME")} \
                ({course_code})')

        except openstack.exceptions.SDKException:
            logging.info(f'Login failed for \
                {username if username else os.getenv("OS_USERNAME")}')
            return False

        if course_code:
            return True

        project = cloud.get_project(
            f'{course_code}-Instructors' if course_code
            else os.getenv('OS_PROJECT_NAME'))

        return cloud, project

    # ------------------------------------------------------------------------
    # Public Getters

    @requires_course_code
    def get_users(self, course_code, instructors=False, students=False,
                  groups=False, details=False, **kwargs):

        if details:
            users = {'instructors': {}, 'students': {}, 'groups': {}}
        else:
            users = {'instructors': [], 'students': [], 'groups': []}

        if students or groups:

            for p in self._cloud.identity.projects(
                     parent_id=kwargs.get('course_project').id):

                if 'Group' in p.name:

                    group_name = int(p.name.split('-')[-1:][0])

                    if details:
                        users['groups'][group_name] = []
                        for u in self._cloud.identity.role_assignments(
                                 scope_project_id=p.id,
                                 role_id=Config.OS_USER_ROLE_ID):

                            user = self._get_user(u.user['id'])

                            if not user.id == self._admin_user.id:
                                users['groups'][group_name].append(user)

                    else:
                        users['groups'].append(group_name)

                else:
                    username = p.name.split('-')[-1:][0]
                    if details:
                        users['students'][username] = self._get_user(username)
                    else:
                        users['students'].append(username)

        if instructors:
            for p in self._cloud.identity.role_assignments(
                     scope_project_id=kwargs.get('course_project').id,
                     role_id=Config.OS_USER_ROLE_ID):

                user = self._get_user(p.user['id'])

                if not user.id == self._admin_user.id:
                    if details:
                        users['instructors'][user.name] = user
                    else:
                        users['instructors'].append(user.name)

        return users

    @requires_course_code
    def get_settings(self, course_code, **kwargs):

        try:
            return json.loads(kwargs.get('course_project').description)

        except Exception as e:

            logging.error(f'{course_code}: Could not load settings: {e}')

            self._cloud.identity.update_project(
                kwargs.get('course_project'),
                description=json.dumps(Config.DEFAULT_COURSE_SETTINGS))

            logging.debug(f'{course_code}: Repaired settings')

            return Config.DEFAULT_COURSE_SETTINGS

    @requires_course_code
    def get_images(self, course_code, instructor_only=False, **kwargs):

        images = {'private': [], 'shared': [], 'student': []}

        students = [project.id for project in
                    self._get_student_projects(course_code)]

        for image in self._cloud.image.images():

            if image.owner == kwargs.get('course_project').id:

                if image.visibility == 'shared':
                    images['shared'].append(image)

                elif image.visibility == 'private':
                    images['private'].append(image)

            if image.owner in students:
                images['student'].append(image)

        if instructor_only:
            images.pop('student')

        return images

    # ------------------------------------------------------------------------
    # Internal Getters

    def _get_project(self, course_code, project_name_or_id, create=False,
                     parent_id=None):

        project = self._cloud.get_project(project_name_or_id)

        if not project and create:

            instructor = True if 'Instructor' in project_name_or_id else False

            project = self._cloud.identity.create_project(
                name=project_name_or_id,
                description='Auto-generated Project' if not instructor
                else json.dumps(Config.DEFAULT_COURSE_SETTINGS),
                parent_id=parent_id if parent_id else None,
                domain_id=Config.OS_DOMAIN_ID,
                enabled=True if instructor else False
            )

            logging.info(f'{course_code}: Created new project \
                {project_name_or_id}')

            self._add_user_to_project(course_code, self._admin_user, project)

        return project

    @requires_course_code
    def _get_student_projects(self, course_code, **kwargs):
        return [
            project for project in
            self._cloud.identity.projects(
                parent_id=kwargs.get('course_project').id)
            if 'Group' not in project.name
        ]

    @requires_course_code
    def _get_group_projects(self, course_code, **kwargs):
        return [
            project for project in
            self._cloud.identity.projects(
                parent_id=kwargs.get('course_project').id)
            if 'Group' in project.name
        ]

    def _get_user(self, username, email=None, create=False):

        user = self._cloud.identity.find_user(
                name_or_id=username,
                ignore_missing=True
        )

        if user and create:
            logging.debug(f'User already exists globally: {username}')

        if not user and not create:
            logging.debug(f'User does not exist: {username}')

        if not user and create:

            if not email or \
                    not len(email.split('@')) == 2 or \
                    not email.split('@')[1] in Config.EMAIL_DOMAINS:

                logging.debug(f'Invalid email: {email}')

            else:

                plaintext_password = self._get_new_password()

                user = self._cloud.create_user(
                    username,
                    password=plaintext_password,
                    email=email,
                    description='Auto-generated Account',
                    domain_id=Config.OS_DOMAIN_ID
                )

                logging.info(f'Created new user: {username}')
                self._send_password_reset_email(user, plaintext_password)

        return user

    def _get_image(self, image_name_or_id):

        result = self._cloud.get_image(image_name_or_id)
        if not result:
            logging.debug(f'Image not found: {image_name_or_id}')

        return result

    def _get_new_password(self):
        return ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=12))

    def _get_scheduled_status(self, course_code):

        weekday = datetime.now().strftime('%a')
        course_settings = self.get_settings(course_code)

        if course_settings['weekend'].lower() == 'true' and \
                datetime.now().weekday() >= 5:

            logging.debug(f'Weekend access enabled for course')
            return True

        elif weekday in course_settings['schedule'].keys():

            for schedule in course_settings['schedule'][weekday]:

                logging.debug(f'Found schedule: {schedule}')

                start_time = time(
                    int(schedule.split(':')[0]),
                    int(schedule.split(':')[1]), 0
                )

                end_time = time(
                    int(schedule.split(':')[2]),
                    int(schedule.split(':')[3]), 0
                )

                if start_time <= datetime.now().time() <= end_time:
                    logging.debug('Course currently scheduled')
                    return True
                else:
                    logging.debug('Course not currently scheduled')
                    return False

        else:
            logging.debug('Course not currently scheduled')
            return False

    def _get_vms(self, course_code, students=False, groups=False,
                 project_dict=False):

        servers = []
        servers_as_project_dict = {}

        for project in \
                (self._get_student_projects(course_code) if students else [])\
                + (self._get_group_projects(course_code) if groups else []):

            for server in self._cloud.compute.servers(
                    project_id=project.id, all_projects=True):

                logging.debug(f'{course_code}: Found VM {server.name}')

                if project_dict:
                    if project.name not in servers_as_project_dict:
                        servers_as_project_dict[project.name] = []
                    servers_as_project_dict[project.name].append(server)
                else:
                    servers.append(server)

        if project_dict:
            return servers_as_project_dict
        else:
            return servers

    # ------------------------------------------------------------------------
    # Public Setters

    @requires_course_code
    def set(self, course_code, **kwargs):

        course_settings = self.get_settings(course_code)

        for setting, setting_value in kwargs.items():

            if setting in course_settings and \
                    not setting_value == course_settings[setting]:

                if setting == 'quota':

                    for type_, quota in setting_value.items():

                        for quota_setting, quota_value in quota.items():

                            if quota_setting in \
                                    course_settings['quota'][type_] and \
                                    isinstance(quota_value, int):

                                course_settings['quota'][type_][quota_setting]\
                                    = quota_value

                if setting not in ['schedule', 'quota']:

                    if setting == 'keep' and \
                            Config.DISABLE_STUDENT_VM_SAVE:
                        pass
                    elif setting == 'snapshots' and \
                            Config.DISABLE_STUDENT_VM_SAVE:
                        pass
                    else:
                        course_settings[setting] = setting_value

        try:

            self._cloud.identity.update_project(
                kwargs.get('course_project'),
                description=json.dumps(course_settings))

            logging.info(f'{course_code}: Updated settings')
            return True

        except Exception as e:
            logging.error(f'{course_code}: Failed to update settings: {e}')
            return False

    @requires_course_code
    @requires_instructor_or_student
    def set_password(self, course_code, username, password=None, **kwargs):

        plaintext_password = password if password else self._get_new_password()

        self._cloud.identity.update_user(
            kwargs.get('user'),
            password=plaintext_password
        )

        logging.info(f'{course_code}: Reset password for {username}')
        self._send_password_reset_email(kwargs.get('user'), plaintext_password)

        return True

    @requires_course_code
    def set_quota(self, course_code, students=False, groups=False, **kwargs):

        if not (students or groups):
            logging.debug('Must specify students or groups when setting quota')
            return False

        student_quota, group_quota = \
            self.get_settings(course_code)['quota'].values()

        if students:
            for project in self._get_student_projects(course_code):
                self._set_project_quota(course_code, project, student_quota)

        if groups:
            for project in self._get_group_projects(course_code):
                self._set_project_quota(course_code, project, group_quota)

        logging.debug(f'{course_code}: Updated quotas')
        return True

    @requires_course_code
    def set_access(self, course_code, project=None, students=False,
                   groups=False, enabled=False, **kwargs):

        if project:
            if not project.is_enabled == enabled:
                self._cloud.identity.update_project(project, enabled=enabled)
                logging.debug(f'{course_code}: Updated project access for {project.name}:\
                    {enabled}')
                return True
            else:
                return False

        course_settings = self.get_settings(course_code)
        weekend = True if (int(datetime.now().strftime('%w'))-1) >= 5 \
            else False

        if students:

            if enabled:

                for project in self._get_student_projects(course_code):
                    if not project.is_enabled:
                        self._cloud.identity.update_project(project,
                                                            enabled=True)
                if not weekend and course_settings['keep']:
                    self._unshelve_vms(course_code, students=True)

            else:

                if not course_settings['keep']:
                    self.remove_student_vms(course_code)
                else:
                    self._shelve_vms(course_code, students=True)

                for project in self._get_student_projects(course_code):
                    if project.is_enabled:
                        self._cloud.identity.update_project(project,
                                                            enabled=False)

        if groups:

            if not enabled:
                self._shelve_vms(course_code, groups=True)

            for project in self._get_group_projects(course_code):
                if not project.is_enabled == enabled:
                    self._cloud.identity.update_project(
                        project, enabled=enabled)

        logging.debug(f'{course_code}: Updated project access for {course_code}:\
                     {enabled}')

        return True

    # ------------------------------------------------------------------------
    # Internal Setters

    def _set_project_quota(self, course_code, project, quota):

        self._cloud.set_compute_quotas(
            name_or_id=project.id,
            instances=quota['instances'],
            cores=quota['cores'],
            ram=quota['ram'])

        self._cloud.set_network_quotas(
            name_or_id=project.id,
            network=quota['network'])

        logging.info(f'{course_code}: Updated quota for {project.name}')

    # ------------------------------------------------------------------------
    # Public Adders

    def add_course(self, course_code):

        if course_code in self.courses:
            logging.debug(f'{course_code}: Course already exists')
            return False

        self._get_project(course_code, f'{course_code}-Instructors',
                          create=True)
        return True

    @requires_course_code
    def add_user(self, course_code, username, email, instructor=False,
                 **kwargs):

        user = self._get_user(str(username), email=str(email), create=True)
        if not user:
            return False

        if not instructor:

            project = self._get_project(
                course_code,
                f'{course_code}-{username}',
                create=True,
                parent_id=kwargs.get('course_project').id
            )

        return self._add_user_to_project(course_code, user,
                                         kwargs.get('course_project')
                                         if instructor else project,
                                         instructor=instructor)

    @requires_course_code
    @requires_student
    def add_student_to_group(self, course_code, username, group_number,
                             **kwargs):

        try:
            if not int(group_number) > 0:
                raise ValueError()
        except ValueError:
            logging.debug(f'{course_code}: Invalid group number: \
                {group_number}')
            return False

        project = self._get_project(
            course_code,
            f'{course_code}-Group-{group_number}',
            create=True,
            parent_id=kwargs.get('course_project').id
        )
        if not project:
            return False

        return self._add_user_to_project(course_code, kwargs.get('user'),
                                         project)

    @requires_course_code
    def add_schedule(self, course_code, day, start_hour, start_minute,
                     end_hour, end_minute, **kwargs):

        try:

            if not isinstance(day, int) or not 0 <= int(day) <= 6:
                raise ValueError('Invalid day of week')

            day = str(day)

            start_time = time(int(start_hour), int(start_minute), 0)
            end_time = time(int(end_hour), int(end_minute), 0)

            if not start_time < end_time:
                raise ValueError('Start time must be before end time')

            course_settings = self.get_settings(course_code)
            scheduled = f'{start_hour}:{start_minute}:{end_hour}:{end_minute}'

            if day in course_settings['schedule'].keys():
                if scheduled in course_settings['schedule'][day]:
                    raise ValueError(f'Schedule already exists on {day} \
                    {start_hour}:{start_minute} - {end_hour}:{end_minute}')
            else:
                course_settings['schedule'][day] = []

            course_settings['schedule'][day].append(scheduled)

            self._cloud.identity.update_project(
                kwargs.get('course_project'),
                description=json.dumps(course_settings))

            logging.info(f'{course_code}: Added new schedule on {day} \
                        {start_hour}:{start_minute} - {end_hour}:{end_minute}')
            return True

        except Exception as e:
            logging.error(f'{course_code}: Failed to add schedule: {e}')
            return False

    # ------------------------------------------------------------------------
    # Internal Adders

    def _add_user_to_project(self, course_code, user, project,
                             instructor=False):

        result = self._cloud.grant_role(
            Config.OS_USER_ROLE_ID,
            user=user.id,
            project=project.id,
            domain=Config.OS_DOMAIN_ID
        )

        if not result:
            logging.debug(f'{course_code}: User {user.name} already in \
                {project.name}')
            return False

        if not user.id == self._admin_user.id:
            self._send_course_enroll_email(course_code, user, project.name,
                                           instructor)
            logging.info(f'{course_code}: Added {user.name} to \
                    {project.name}')

        return True

    # ------------------------------------------------------------------------
    # Public Removers

    @requires_course_code
    def remove_course(self, course_code, **kwargs):

        for project in \
                self._get_student_projects(course_code) + \
                self._get_group_projects(course_code):

            self._remove_project(course_code, project.name)

        result = self._remove_project(
            course_code,
            f'{course_code}-Instructors'
        )

        if result:
            logging.info(f'{course_code}: Removed course')
        else:
            logging.error(f'{course_code}: Failed to remove course')

        return result

    @requires_course_code
    def remove_user(self, course_code, username, group_number=None,
                    instructor=False, **kwargs):

        if group_number:
            project_name = f'{course_code}-Group-{group_number}'
        elif instructor:
            project_name = f'{course_code}-Instructors'
        else:
            project_name = f'{course_code}-{username}'

        project = self._get_project(course_code, project_name)
        if not project:
            logging.debug(f'{course_code}: {username} not enrolled in course')
            return False

        user = self._get_user(username)
        if not user:
            return False

        if group_number or instructor:
            result = self._remove_user_from_project(course_code, user, project)
        else:
            result = self._cloud.delete_project(
                project.name, domain_id=Config.OS_DOMAIN_ID)

        if result:
            logging.info(f'{course_code}: Removed {username} from \
                {project_name}')
        else:
            logging.error(f'{course_code}: Failed to remove {username} from \
                {project_name}')

        return result

    @requires_course_code
    def remove_group(self, course_code, group_number=None, **kwargs):

        result = self._cloud.delete_project(
            f'{course_code}-Group-{group_number}')

        if result:
            logging.info(f'{course_code}: Removed Group-{group_number}')
        else:
            logging.debug(f'{course_code}: Invalid group: {group_number}')

        return result

    @requires_course_code
    def remove_schedule(self, course_code, day, start_hour, start_minute,
                        end_hour, end_minute, **kwargs):

        try:

            if not isinstance(day, int) or not 0 <= int(day) <= 6:
                raise ValueError('Invalid day of week')

            day = str(day)

            course_settings = self.get_settings(course_code)
            scheduled = f'{start_hour}:{start_minute}:{end_hour}:{end_minute}'

            if day in course_settings['schedule'].keys() and \
                    scheduled in course_settings['schedule'][day]:

                loc = course_settings['schedule'][day].index(scheduled)
                del course_settings['schedule'][day][loc]

                if len(course_settings['schedule'][day]) == 0:
                    del course_settings['schedule'][day]

                self._cloud.identity.update_project(
                    kwargs.get('course_project'),
                    description=json.dumps(course_settings))

                logging.info(f'{course_code}: Removed schedule on {day} \
                    {start_hour}:{start_minute} - {end_hour}:{end_minute}')
                return True

            raise ValueError(f'{course_code}: Schedule not found on {day} \
                    {start_hour}:{start_minute} - {end_hour}:{end_minute}')

        except Exception as e:
            logging.error(f'{course_code}: Failed to remove schedule: {e}')
            return False

    @requires_course_code
    def remove_student_snapshots(self, course_code, **kwargs):

        if self.get_settings(course_code)['snapshots']:
            return False

        for image in self.get_images(course_code)['student']:

            project = self._get_project(course_code, image.owner)

            access_toggled = self.set_access(
                    course_code,
                    project=project,
                    enabled=True
            )

            scoped = self._cloud.connect_as_project(project.name)
            result = scoped.delete_image(image.id, wait=False)

            if result:
                logging.debug(f'{course_code}: Removed snapshot {image.name} \
                    from {project.name}')
            else:
                logging.error(f'{course_code}: Failed to remove rogue snapshot \
                    {image.id} from {project.name}')

            if access_toggled:
                self.set_access(course_code, project=project,
                                enabled=False)

        return True

    @requires_course_code
    def remove_student_vms(self, course_code, **kwargs):

        if self.get_settings(course_code)['keep']:
            logging.debug(f'{course_code}: Can\'t remove student VMs: \
                course has saved VMs enabled')
            return False

        for server in self._get_vms(course_code, students=True):

            project = self._get_project(course_code, server.project_id)

            access_toggled = self.set_access(
                    course_code,
                    project=project,
                    enabled=True
            )

            scoped = self._cloud.connect_as_project(project.name)
            result = scoped.delete_server(server.name, delete_ips=True,
                                          wait=True)

            if result:
                logging.debug(f'{course_code}: Deleted student VM \
                    {server.name}')
            else:
                logging.error(f'{course_code}: Failed to delete student VM \
                    "{server.name}"')

            if access_toggled:
                self.set_access(course_code, project=project,
                                enabled=False)

        return True

    # ------------------------------------------------------------------------
    # Internal Removers

    def _remove_user_from_project(self, course_code, user, project):

        result = self._cloud.revoke_role(
            Config.OS_USER_ROLE_ID,
            user=user.id,
            project=project.id,
            domain=Config.OS_DOMAIN_ID
        )

        if result:
            logging.info(f'{course_code}: Removed {user.name} from \
                {project.name}')
        else:
            logging.error(f'{course_code}: Failed to remove {user.name} from \
                {project.name}')

        return result

    def _remove_project(self, course_code, project_name):

        result = self._cloud.delete_project(
            project_name, domain_id=Config.OS_DOMAIN_ID)

        if result:
            logging.info(f'{course_code}: Removed {project_name}')
        else:
            logging.error(f'{course_code}: Failed to remove {project_name}')

        return result

    # ------------------------------------------------------------------------
    # Public Image Share Functions

    @requires_course_code
    @requires_image_in_course
    def share_image(self, course_code, image_name_or_id, **kwargs):

        image = kwargs.get('image')

        if not image.visibility == 'private':
            logging.debug(f'{course_code}: \
                Invalid image or image status for {image.id}')
            return False

        course = self._cloud.connect_as_project(f'{course_code}-Instructors')

        try:
            course.image.update_image(image, visibility='shared')
            logging.info(f'{course_code}: Shared image {image.name}')

        except Exception as e:
            logging.error(f'{course_code}: Error sharing image {image.name}:\
                 {e}')
            return False

        projects = self._get_student_projects(course_code) + \
            self._get_group_projects(course_code)

        for project in projects:

            try:

                try:
                    course.image.add_member(image.id, member_id=project.id)
                    logging.debug(f'{course_code}: Shared image {image.name} with \
                        {project.name}')
                except Exception as e:
                    logging.error(f'{course_code}: Sharing image {image.name} with \
                        {project.name}: {e}')

                access_toggled = self.set_access(
                    course_code,
                    project=project,
                    enabled=True
                )

                try:
                    student = self._cloud.connect_as_project(project.name)
                    student.image.update_member(
                            project.id,
                            image.id,
                            status='accepted'
                    )
                    logging.debug(f'{course_code}: Accepted {image.name} \
                    for {project.name}')

                except Exception as e:
                    logging.error(f'{course_code}: Sharing image {image.name} with \
                        {project.name}: {e}')

                if access_toggled:
                    self.set_access(course_code, project=project,
                                    enabled=False)
            except Exception as e:
                logging.error(f'{course_code}: Failed to accept {image.name} \
                    for {project.name}: {e}')

        return True

    @requires_course_code
    @requires_image_in_course
    def unshare_image(self, course_code, image_name_or_id, **kwargs):

        image = kwargs.get('image')

        if not image.visibility == 'shared':
            logging.debug(f'{course_code}: \
                Invalid image or image status for {image.id}')
            return False

        course = self._cloud.connect_as_project(f'{course_code}-Instructors')

        for item in self._cloud.image.members(image.id):

            try:
                member_id = item['member_id']
                course.image.remove_member(member_id, image.id)
                logging.debug(f'Removed access to image {image.name} \
                    for {member_id}')

            except Exception as e:
                logging.error(f'Failed to remove access to image {image.name} \
                    for {member_id}: {e}')

        try:
            course.image.update_image(image, visibility='private')
            logging.info(f'{course_code}: Unshared image {image.name}')
            return True

        except Exception as e:
            logging.error(f'{course_code}: Error unsharing image {image.name}:\
                 {e}')
            return False

    # ------------------------------------------------------------------------
    # Public Shelve Functions

    @requires_course_code
    def _shelve_vms(self, course_code, students=False, groups=False, **kwargs):

        logging.debug(f'{course_code}: Shelving VMs \
            (students: {students}, groups: {groups})')

        for server in self._get_vms(course_code, students=students,
                                    groups=groups):

            if server.status not in ['ACTIVE', 'STOPPED', 'SUSPENDED']:
                continue

            project = self._get_project(course_code, server.project_id)

            access_toggled = self.set_access(
                course_code,
                project=project,
                enabled=True
            )

            scoped = self._cloud.connect_as_project(project.name)
            scoped.compute.shelve_server(server)

            if access_toggled:
                self.set_access(course_code, project=project, enabled=False)

            logging.debug(f'{course_code}: Shelved VM {server.name}')

        logging.debug(f'{course_code}: Finished shelving VMs')
        return True

    @requires_course_code
    def _unshelve_vms(self, course_code, students=False, groups=False,
                      **kwargs):

        logging.debug(f'{course_code}: Unshelving VMs \
            (students: {students}, groups: {groups})')

        for server in self._get_vms(course_code, students=students,
                                    groups=groups):

            if not server.status == 'SHELVED_OFFLOADED':
                continue

            project = self._get_project(course_code, server.project_id)
            scoped = self._cloud.connect_as_project(project.name)

            scoped.compute.unshelve_server(server)
            logging.debug(f'{course_code}: Unshelved VM {server.name}')

        logging.debug(f'{course_code}: Finished unshelving VMs')
        return True

    # ------------------------------------------------------------------------
    # Public Status Functions

    @requires_course_code
    def is_running(self, course_code, **kwargs):

        weekday = str(int(datetime.now().strftime('%w')) - 1)
        course_settings = self.get_settings(course_code)

        if 'weekend' not in course_settings.keys() or \
                'schedule' not in course_settings.keys():

            self._cloud.identity.update_project(
                kwargs.get('course_project'),
                description=json.dumps(Config.DEFAULT_COURSE_SETTINGS))

            logging.debug(f'{course_code}: Repaired settings')
            return False

        if course_settings['weekend'] and datetime.now().weekday() >= 5:
            logging.debug(f'{course_code}: Weekend access enabled for course')
            return True

        elif weekday in course_settings['schedule'].keys():

            for schedule in course_settings['schedule'][weekday]:

                logging.debug(f'{course_code}: Found schedule: {schedule}')

                start_time = time(
                    int(schedule.split(':')[0]),
                    int(schedule.split(':')[1]), 0
                )

                end_time = time(
                    int(schedule.split(':')[2]),
                    int(schedule.split(':')[3]), 0
                )

                if start_time <= datetime.now().time() <= end_time:
                    logging.debug(f'{course_code}: Course currently scheduled')
                    return True
                else:
                    logging.debug(f'{course_code}: Course not scheduled')
                    return False

        return False

    # ------------------------------------------------------------------------
    # Public Email Functions

    @requires_course_code
    @requires_instructor_or_student
    def send_password_reset_request_email(self, course_code, username, token,
                                          **kwargs):
        user = kwargs.get('user')

        file = open(os.path.join(
            current_dir, 'templates/email/password_reset_request.template'))

        message = file.read().format(
            cloud_url=Config.CLOUD_URL,
            token=token)

        logging.info(f'Sent password reset request email to {user.email}')
        self._send_email(user.email, 'Password Reset Request', message)

    # ------------------------------------------------------------------------
    # Internal Email Functions

    def _send_password_reset_email(self, user, plaintext_password):

        file = open(os.path.join(
            current_dir, 'templates/email/password_reset.template'))

        message = file.read().format(
            username=user.name,
            password=plaintext_password,
            cloud_url=Config.CLOUD_URL)

        logging.info(f'Sent password reset email to {user.email}')
        self._send_email(user.email, 'Private Cloud Account Details', message)

    def _send_course_enroll_email(self, course_code, user, project_name,
                                  instructor=False):

        if instructor:
            file = open(os.path.join(
                current_dir, 'templates/email/instructor.template'))
        else:
            file = open(os.path.join(
                current_dir, 'templates/email/registration.template'))

        message = file.read().format(
            course=course_code,
            username=user.name,
            project=project_name,
            cloud_url=Config.CLOUD_URL,
            course_manager_url=Config.COURSE_MANAGER_URL,
            vpn_client_url=Config.VPN_CLIENT_URL,
            vpn_file_url=Config.VPN_FILE_URL,
            vpn_setup_guide=Config.VPN_SETUP_GUIDE)

        logging.info(f'{course_code}: Sending course enroll email to \
            {user.email}')

        self._send_email(user.email, f'Added to Cloud Course: {course_code}',
                         message)

    def _send_email(self, recipient, subject, message):

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg['From'] = formataddr((str(Header('Cloud Bot', 'utf-8')),
                                 Config.EMAIL_SENDER))
        msg["To"] = recipient
        msg.attach(MIMEText(message, "html"))

        context = ssl.create_default_context()

        try:

            server = smtplib.SMTP(Config.EMAIL_SERVER, Config.EMAIL_PORT)
            server.ehlo()

            if Config.EMAIL_USE_TLS:
                server.starttls(context=context)
                server.ehlo()

            if Config.EMAIL_USERNAME and Config.EMAIL_PASSWORD:
                server.login(Config.EMAIL_USERNAME, Config.EMAIL_PASSWORD)

            server.sendmail(Config.EMAIL_SENDER, recipient, msg.as_string())
            server.quit()

        except Exception as e:
            logging.error(f'Failed to send message to {recipient}: {e}')

    # ------------------------------------------------------------------------
