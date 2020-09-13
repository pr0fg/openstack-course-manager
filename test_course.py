#!/usr/bin/env python

# OpenStack Course Manager  Copyright (C) 2020  Garrett Hayes
import random
import string
import os
from datetime import datetime, time

from classes import OpenStackCourse
from config import Config


def generate_random_value(length):
    return ''.join(random.choices(string.digits, k=length))


course_code = f'INFR-9{generate_random_value(3)}'
project_name = f'{course_code}-Instructors'
student_id = f'1009{generate_random_value(5)}'
student_email = f'{student_id}@{Config.EMAIL_DOMAINS[1]}'
instructor_id = f'pytest{generate_random_value(3)}'
instructor_email = f'{instructor_id}@{Config.EMAIL_DOMAINS[0]}'
image_name = f'pytest{generate_random_value(3)}'
manager = None
admin_user = None


def test_setup():

    global manager, admin_user

    manager = OpenStackCourse()
    assert manager

    admin_user = manager._get_user(os.getenv('OS_USERNAME'))
    assert admin_user

    assert manager.add_course(course_code)


# def test_course():

#     assert not manager.add_course(course_code)

#     project = manager._get_project(course_code, project_name)
#     assert project
#     assert project.is_enabled

#     admin_user = manager._get_user(os.getenv('OS_USERNAME'))
#     assert admin_user
#     assert admin_user.is_enabled

#     assert not manager._add_user_to_project(course_code, admin_user, project)

#     settings = manager.get_settings(course_code)
#     assert settings
#     assert settings == Config.DEFAULT_COURSE_SETTINGS


# def test_add_instructor():

#     assert not manager.add_user('bad', instructor_id, instructor_email,
#                                 instructor=True)
#     assert not manager.add_user(course_code, instructor_id, 's@s',
#                                 instructor=True)

#     assert manager.add_user(course_code, instructor_id, instructor_email,
#                             instructor=True)
#     assert not manager.add_user(course_code, instructor_id, instructor_email,
#                                 instructor=True)

#     assert manager.login(
#         course_code=course_code,
#         username=os.getenv('OS_USERNAME'),
#         password=os.getenv('OS_PASSWORD')
#     )

#     user = manager._get_user(instructor_id)
#     assert user
#     assert user.is_enabled
#     assert user.name == instructor_id
#     assert user.email == instructor_email

#     project = manager._get_project(course_code, project_name)
#     assert not manager._add_user_to_project(course_code, user, project)

#     assert manager.remove_user(course_code, instructor_id, instructor=True)
#     assert not manager.remove_user(course_code, instructor_id, instructor=True)


# def test_add_student():

#     assert manager.add_user(course_code, student_id, student_email)
#     assert not manager.add_user(course_code, student_id, student_email)

#     user = manager._get_user(student_id)
#     assert user
#     assert user.is_enabled
#     assert user.name == student_id
#     assert user.email == student_email

#     project = manager._get_project(course_code, f'{course_code}-{student_id}')
#     assert project
#     assert project.is_enabled
#     assert project.name == f'{course_code}-{student_id}'

#     assert not manager._add_user_to_project(course_code, user, project)

#     assert not manager.set_password(course_code, 'sdsdaas')
#     assert manager.set_password(course_code, student_id,
#                                 password=os.getenv('OS_PASSWORD'))

#     assert not manager.remove_user(course_code, 'dsadd')
#     assert manager.remove_user(course_code, student_id)
#     assert not manager.remove_user(course_code, student_id)


# def test_add_student_to_group():

#     assert manager.add_user(course_code, student_id, student_email)

#     assert not manager.add_student_to_group(course_code, student_id, 0)
#     assert not manager.add_student_to_group(course_code, student_id, 'ssss')

#     assert manager.add_student_to_group(course_code, student_id, 1)
#     assert not manager.add_student_to_group(course_code, student_id, 1)

#     project = manager._get_project(course_code, f'{course_code}-Group-1')
#     assert project
#     assert project.is_enabled

#     user = manager._get_user(student_id)
#     assert not manager._add_user_to_project(course_code, user, project)

#     assert not manager.remove_user(course_code, student_id, group_number=7)
#     assert not manager.remove_user(course_code, 'sdsda', group_number=1)
#     assert manager.remove_user(course_code, student_id, group_number=1)
#     assert not manager.remove_user(course_code, student_id, group_number=1)

#     assert manager.add_student_to_group(course_code, student_id, 1)
#     assert not manager.remove_group(course_code, 2)
#     assert manager.remove_group(course_code, 1)
#     assert not manager.remove_group(course_code, 1)

#     assert manager.remove_user(course_code, student_id)


# def test_password_reset():

#     assert manager.add_user(course_code, student_id, student_email)

#     assert not manager.set_password(course_code, 'saddsaads')
#     assert manager.set_password(course_code, student_id,
#                                 password=os.getenv('OS_PASSWORD'))

#     assert manager.remove_user(course_code, student_id)


# def test_settings():

#     assert manager.set(course_code, keep=True, snapshots=True, bad=True)

#     settings = manager.get_settings(course_code)
#     assert 'bad' not in settings

#     assert bool(settings['keep'])
#     assert bool(settings['weekend'])
#     assert bool(settings['snapshots'])


# def test_access_controls():

#     assert manager.add_user(course_code, student_id, student_email)
#     assert manager.add_student_to_group(course_code, student_id, 1)

#     assert manager._get_project(
#         course_code, f'{course_code}-{student_id}').is_enabled
#     assert manager._get_project(
#         course_code, f'{course_code}-Group-1').is_enabled

#     assert manager.disable_students(course_code)
#     assert not manager._get_project(
#         course_code, f'{course_code}-{student_id}').is_enabled
#     assert manager._get_project(
#         course_code, f'{course_code}-Group-1').is_enabled

#     assert manager.disable_groups(course_code)
#     assert not manager._get_project(
#         course_code, f'{course_code}-{student_id}').is_enabled
#     assert not manager._get_project(
#         course_code, f'{course_code}-Group-1').is_enabled

#     assert manager.enable_students(course_code)
#     assert manager._get_project(
#         course_code, f'{course_code}-{student_id}').is_enabled
#     assert not manager._get_project(
#         course_code, f'{course_code}-Group-1').is_enabled

#     assert manager.enable_groups(course_code)
#     assert manager._get_project(
#         course_code, f'{course_code}-{student_id}').is_enabled
#     assert manager._get_project(
#         course_code, f'{course_code}-Group-1').is_enabled

#     assert manager.remove_group(course_code, 1)
#     assert manager.remove_user(course_code, student_id)


# def test_schedule():

#     assert not manager.add_schedule(course_code, 1, 9, 0, 8, 0)
#     assert not manager.add_schedule(course_code, -1, 9, 0, 11, 0)
#     assert not manager.add_schedule(course_code, 'jac', 9, 0, 11, 0)
#     assert not manager.add_schedule(course_code, 1, 9, 0, 25, 0)

#     assert manager.add_schedule(course_code, 1, 9, 0, 11, 0)
#     assert not manager.add_schedule(course_code, 1, 9, 0, 11, 0)
#     assert manager.add_schedule(course_code, 2, 11, 0, 15, 0)

#     assert '9:0:11:0' in manager.get_settings(course_code)['schedule']['Tue']
#     assert '11:0:15:0' in manager.get_settings(course_code)['schedule']['Wed']

#     assert not manager.remove_schedule(course_code, 0, 9, 0, 11, 0)
#     assert manager.remove_schedule(course_code, 1, 9, 0, 11, 0)
#     assert not manager.remove_schedule(course_code, 1, 9, 0, 11, 0)
#     assert manager.remove_schedule(course_code, 2, 11, 0, 15, 0)

#     assert '9:0:11:0' not in \
#         manager.get_settings(course_code)['schedule']['Tue']
#     assert '11:0:15:0' not in \
#         manager.get_settings(course_code)['schedule']['Wed']

#     assert not manager.is_running(course_code)
#     now = datetime.now().time()
#     weekday = datetime.now().weekday()
#     assert manager.add_schedule(course_code, weekday, now.hour, now.minute,
#                                 now.hour + 1, now.minute)
#     assert manager.is_running(course_code)


# def test_images():

#     assert manager.add_user(course_code, student_id, student_email)
#     assert manager.add_student_to_group(course_code, student_id, 1)

#     course_scoped = manager._cloud.connect_as_project(
#                         f'{project_name}')

#     tmp_image = course_scoped.image.create_image(
#         name=image_name, use_import=True,
#         disk_format='qcow2', container_format='bare',
#         allow_duplicates=False, visibility='private'
#     )
#     assert tmp_image

#     course_scoped.image.import_image(
#         tmp_image, method='web-download',
#         uri='http://download.cirros-cloud.net/0.4.0/\
#         cirros-0.4.0-x86_64-disk.img'
#     )

#     image = manager._get_image(tmp_image.id)
#     assert image.visibility == 'private'

#     assert manager.share_image(course_code, image.id)

#     spid = manager._get_project(course_code, f'{course_code}-{student_id}').id
#     gpid = manager._get_project(course_code, f'{course_code}-Group-1').id

#     image = manager._get_image(tmp_image.id)
#     image_members = [
#         item['member_id'] if item['status'] == 'accepted' else None
#         for item in list(manager._cloud.image.members(image.id))
#     ]

#     assert image.visibility == 'shared'
#     assert spid in image_members
#     assert gpid in image_members

#     assert manager.unshare_image(course_code, image.id)

#     image = manager._get_image(tmp_image.id)
#     assert image.visibility == 'private'

#     assert manager._cloud.delete_image(image.id)

#     assert manager.remove_group(course_code, 1)
#     assert manager.remove_user(course_code, student_id)


def test_quotas():

    assert manager.add_user(course_code, student_id, student_email)
    assert manager.add_student_to_group(course_code, student_id, 1)

    quota = {
        'students': {
            'instances': 2,
            'cores': 3,
            'ram': 4,
            'network': 5,
            'bad': 'bad'
        },
        'groups': {
            'instances': 6,
            'cores': 7,
            'ram': 8,
            'network': 9,
            'bad': 'bad'
        }
    }

    assert manager.set(course_code, quota=quota)

    for type_ in quota.keys():
        for key, value in quota[type_].items():
            if key == 'bad':
                assert 'bad' not in \
                    manager.get_settings(course_code)['quota'][type_].keys()
            else:
                assert manager.get_settings(course_code)['quota'][type_][key] \
                    == quota[type_][key]

    assert manager.set_quota(students=True, groups=True)

    spid = manager._get_project(
        course_code, f'{course_code}-{student_id}').id
    gpid = manager._get_project(
        course_code, f'{course_code}-Group-1').id

    student_quota_compute = manager._cloud.get_compute_quotas(spid)
    student_quota_networks = manager._cloud.get_network_quotas(spid)
    group_quota_compute = manager._cloud.get_compute_quotas(gpid)
    group_quota_networks = manager._cloud.get_network_quotas(gpid)

    for type_ in quota.keys():
        for key, value in quota[type_].items():
            if key == 'bad':
                pass
            elif type_ == 'students':
                if key == 'network':
                    assert quota[type_][key] == student_quota_networks[key]
                else:
                    assert quota[type_][key] == student_quota_compute[key]
            else:
                if key == 'network':
                    assert quota[type_][key] == group_quota_networks[key]
                else:
                    assert quota[type_][key] == group_quota_compute[key]

    assert manager.remove_group(course_code, 1)
    assert manager.remove_user(course_code, student_id)


# def test_remove_rogue_snapshots():

#     course, course_code, project_name = generate_course()
#     name, email = generate_student()

#     assert manager.add_student(name, email)
#     assert manager.remove_snapshots()

#     assert manager.set(snapshots=True)
#     assert not manager.remove_snapshots()

#     assert manager.remove()


def test_remove_course():

    assert manager.remove_course(course_code)
    assert not manager.remove_course(course_code)
    assert not manager._get_project(course_code, project_name)

    instructor = manager._get_user(instructor_id)
    student = manager._get_user(student_id)

    if instructor:
        manager._cloud.identity.delete_user(instructor.id, ignore_missing=True)
    if student:
        manager._cloud.identity.delete_user(student.id, ignore_missing=True)
