#!/usr/bin/env python

# OpenStack Course Manager  Copyright (C) 2020  Garrett Hayes

import random
import string
import os
import time
from datetime import datetime

from classes import OpenStackCourseManager
from config import Config


def generate_random_value(length):
    return ''.join(random.choices(string.digits, k=length))


course_code = f'INFR-9{generate_random_value(3)}'
project_name = f'{course_code}-Instructors'
pytest_number = generate_random_value(3)

student_id = f'1009{generate_random_value(5)}'
student_email = f'{student_id}@{Config.EMAIL_DOMAINS[1]}'
instructor_id = f'pytest{pytest_number}'
instructor_email = f'{instructor_id}@{Config.EMAIL_DOMAINS[0]}'
image_name = f'pytest{pytest_number}'
vm_name = f'pytest{pytest_number}'

manager = OpenStackCourseManager()
assert manager

admin_user = manager._get_user(os.getenv('OS_USERNAME'))
assert admin_user

assert manager.add_course(course_code)


def test_course():

    assert not manager.add_course(course_code)

    project = manager._get_project(course_code, project_name)
    assert project
    assert project.is_enabled

    admin_user = manager._get_user(os.getenv('OS_USERNAME'))
    assert admin_user
    assert admin_user.is_enabled

    assert not manager._add_user_to_project(course_code, admin_user, project)

    settings = manager.get_settings(course_code)
    assert settings
    assert settings == Config.DEFAULT_COURSE_SETTINGS


def test_add_instructor():

    assert not manager.add_user('bad', instructor_id, instructor_email,
                                instructor=True)
    assert not manager.add_user(course_code, instructor_id, 's@s',
                                instructor=True)

    assert manager.add_user(course_code, instructor_id, instructor_email,
                            instructor=True)
    assert not manager.add_user(course_code, instructor_id, instructor_email,
                                instructor=True)

    assert manager.login(
        course_code=course_code,
        username=os.getenv('OS_USERNAME'),
        password=os.getenv('OS_PASSWORD')
    )

    user = manager._get_user(instructor_id)
    assert user
    assert user.is_enabled
    assert user.name == instructor_id
    assert user.email == instructor_email

    project = manager._get_project(course_code, project_name)
    assert not manager._add_user_to_project(course_code, user, project)

    assert manager.remove_user(course_code, instructor_id, instructor=True)
    assert not manager.remove_user(course_code, instructor_id, instructor=True)


def test_add_student():

    assert manager.add_user(course_code, student_id, student_email)
    assert not manager.add_user(course_code, student_id, student_email)

    user = manager._get_user(student_id)
    assert user
    assert user.is_enabled
    assert user.name == student_id
    assert user.email == student_email

    project = manager._get_project(course_code, f'{course_code}-{student_id}')
    assert project
    assert project.is_enabled
    assert project.name == f'{course_code}-{student_id}'

    assert not manager._add_user_to_project(course_code, user, project)

    assert not manager.set_password(course_code, 'sdsdaas')
    assert manager.set_password(course_code, student_id,
                                password=os.getenv('OS_PASSWORD'))

    assert not manager.remove_user(course_code, 'dsadd')
    assert manager.remove_user(course_code, student_id)
    assert not manager.remove_user(course_code, student_id)


def test_add_student_to_group():

    assert manager.add_user(course_code, student_id, student_email)

    assert not manager.add_student_to_group(course_code, student_id, 0)
    assert not manager.add_student_to_group(course_code, student_id, 'ssss')

    assert manager.add_student_to_group(course_code, student_id, 1)
    assert not manager.add_student_to_group(course_code, student_id, 1)

    project = manager._get_project(course_code, f'{course_code}-Group-1')
    assert project
    assert project.is_enabled

    user = manager._get_user(student_id)
    assert not manager._add_user_to_project(course_code, user, project)

    assert not manager.remove_user(course_code, student_id, group_number=7)
    assert not manager.remove_user(course_code, 'sdsda', group_number=1)
    assert manager.remove_user(course_code, student_id, group_number=1)
    assert not manager.remove_user(course_code, student_id, group_number=1)

    assert manager.add_student_to_group(course_code, student_id, 1)
    assert not manager.remove_group(course_code, 2)
    assert manager.remove_group(course_code, 1)
    assert not manager.remove_group(course_code, 1)

    assert manager.remove_user(course_code, student_id)


def test_password_reset():

    assert manager.add_user(course_code, student_id, student_email)

    assert not manager.set_password(course_code, 'saddsaads')
    assert manager.set_password(course_code, student_id,
                                password=os.getenv('OS_PASSWORD'))

    assert manager.remove_user(course_code, student_id)


def test_settings():

    assert manager.set(course_code, keep=True, snapshots=True, bad=True)

    settings = manager.get_settings(course_code)
    assert 'bad' not in settings

    assert bool(settings['keep'])
    assert bool(settings['weekend'])
    assert bool(settings['snapshots'])


def test_access_controls():

    assert manager.add_user(course_code, student_id, student_email)
    assert manager.add_student_to_group(course_code, student_id, 1)

    assert manager._get_project(
        course_code, f'{course_code}-{student_id}').is_enabled
    assert manager._get_project(
        course_code, f'{course_code}-Group-1').is_enabled

    assert manager.disable_students(course_code)
    assert not manager._get_project(
        course_code, f'{course_code}-{student_id}').is_enabled
    assert manager._get_project(
        course_code, f'{course_code}-Group-1').is_enabled

    assert manager.disable_groups(course_code)
    assert not manager._get_project(
        course_code, f'{course_code}-{student_id}').is_enabled
    assert not manager._get_project(
        course_code, f'{course_code}-Group-1').is_enabled

    assert manager.enable_students(course_code)
    assert manager._get_project(
        course_code, f'{course_code}-{student_id}').is_enabled
    assert not manager._get_project(
        course_code, f'{course_code}-Group-1').is_enabled

    assert manager.enable_groups(course_code)
    assert manager._get_project(
        course_code, f'{course_code}-{student_id}').is_enabled
    assert manager._get_project(
        course_code, f'{course_code}-Group-1').is_enabled

    assert manager.remove_group(course_code, 1)
    assert manager.remove_user(course_code, student_id)


def test_schedule():

    assert not manager.add_schedule(course_code, 1, 9, 0, 8, 0)
    assert not manager.add_schedule(course_code, -1, 9, 0, 11, 0)
    assert not manager.add_schedule(course_code, 'jac', 9, 0, 11, 0)
    assert not manager.add_schedule(course_code, 1, 9, 0, 25, 0)

    assert manager.add_schedule(course_code, 1, 9, 0, 11, 0)
    assert not manager.add_schedule(course_code, 1, 9, 0, 11, 0)
    assert manager.add_schedule(course_code, 2, 11, 0, 15, 0)

    assert '9:0:11:0' in manager.get_settings(course_code)['schedule']['Tue']
    assert '11:0:15:0' in manager.get_settings(course_code)['schedule']['Wed']

    assert not manager.remove_schedule(course_code, 0, 9, 0, 11, 0)
    assert manager.remove_schedule(course_code, 1, 9, 0, 11, 0)
    assert not manager.remove_schedule(course_code, 1, 9, 0, 11, 0)
    assert manager.remove_schedule(course_code, 2, 11, 0, 15, 0)

    assert '9:0:11:0' not in \
        manager.get_settings(course_code)['schedule']['Tue']
    assert '11:0:15:0' not in \
        manager.get_settings(course_code)['schedule']['Wed']

    assert not manager.is_running(course_code)
    now = datetime.now().time()
    weekday = datetime.now().weekday()
    assert manager.add_schedule(course_code, weekday, now.hour, now.minute,
                                now.hour + 1, now.minute)
    assert manager.is_running(course_code)


def test_images():

    assert manager.add_user(course_code, student_id, student_email)
    assert manager.add_student_to_group(course_code, student_id, 1)

    course_scoped = manager._cloud.connect_as_project(
                        f'{project_name}')

    tmp_image = course_scoped.image.create_image(
        name=image_name, use_import=True,
        disk_format='qcow2', container_format='bare',
        allow_duplicates=False, visibility='private'
    )
    assert tmp_image

    course_scoped.image.import_image(
        tmp_image, method='web-download',
        uri='http://download.cirros-cloud.net/0.4.0/\
        cirros-0.4.0-x86_64-disk.img'
    )

    image = manager._get_image(tmp_image.id)
    assert image.visibility == 'private'

    assert manager.share_image(course_code, image.id)

    spid = manager._get_project(course_code, f'{course_code}-{student_id}').id
    gpid = manager._get_project(course_code, f'{course_code}-Group-1').id

    image = manager._get_image(tmp_image.id)
    image_members = [
        item['member_id'] if item['status'] == 'accepted' else None
        for item in list(manager._cloud.image.members(image.id))
    ]

    assert image.visibility == 'shared'
    assert spid in image_members
    assert gpid in image_members

    assert manager.unshare_image(course_code, image.id)

    image = manager._get_image(tmp_image.id)
    assert image.visibility == 'private'

    assert manager._cloud.delete_image(image.id)

    assert manager.remove_group(course_code, 1)
    assert manager.remove_user(course_code, student_id)


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

    assert manager.set_quota(course_code, students=True, groups=True)

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


def test_remove_snapshots_and_servers():

    assert manager.add_user(course_code, student_id, student_email)

    student_scope = manager._cloud.connect_as_project(
                        f'{course_code}-{student_id}')

    student_server = student_scope.create_server(
        f'{vm_name}-student',
        image=Config.OS_TEST_IMAGE_ID,
        flavor=Config.OS_TEST_IMAGE_FLAVOR_ID,
        wait=True
    )
    assert student_server

    student_snapshot = student_scope.create_image_snapshot(
        f'{vm_name}-student',
        student_server.id,
        wait=True
    )
    assert student_snapshot
    assert student_snapshot.id in \
        [image.id for image in manager.get_images(course_code)['student']]

    assert manager.set(course_code, snapshots=False)
    assert manager.remove_student_snapshots(course_code)
    assert student_snapshot.id not in \
        [image.id for image in manager.get_images(course_code)['student']]

    assert manager.set(course_code, snapshots=True)
    assert not manager.remove_student_snapshots(course_code)

    assert manager.set(course_code, keep=True)
    assert not manager.remove_student_vms(course_code)

    assert manager.set(course_code, keep=False)
    assert manager.remove_student_vms(course_code)

    assert not manager._cloud.get_server(
        name_or_id=f'{vm_name}-student', all_projects=True)

    assert manager._cloud.delete_server(student_server.id)

    assert manager.remove_user(course_code, student_id)


def test_shelving():

    assert manager.add_user(course_code, student_id, student_email)
    assert manager.add_student_to_group(course_code, student_id, 1)

    student_scope = manager._cloud.connect_as_project(
                        f'{course_code}-{student_id}')
    group_scope = manager._cloud.connect_as_project(
                        f'{course_code}-Group-1')

    student_server = student_scope.create_server(
        f'{vm_name}-student',
        image=Config.OS_TEST_IMAGE_ID,
        flavor=Config.OS_TEST_IMAGE_FLAVOR_ID,
        wait=True
    )
    assert student_server

    group_server = group_scope.create_server(
        f'{vm_name}-group',
        image=Config.OS_TEST_IMAGE_ID,
        flavor=Config.OS_TEST_IMAGE_FLAVOR_ID,
        wait=True
    )
    assert group_server

    assert manager.set(course_code, keep=False)
    assert not manager.shelve_vms(course_code)

    assert manager.set(course_code, keep=True)
    assert manager.shelve_vms(course_code, students=True)
    time.sleep(60)

    assert 'SHELV' in \
        manager._cloud.compute.get_server(student_server.id).status

    assert manager.shelve_vms(course_code, groups=True)
    time.sleep(60)

    assert 'SHELV' in \
        manager._cloud.compute.get_server(group_server.id).status

    assert manager.unshelve_vms(course_code, students=True, groups=True)
    time.sleep(60)

    assert 'ACTIVE' in \
        manager._cloud.compute.get_server(student_server.id).status

    assert 'ACTIVE' in \
        manager._cloud.compute.get_server(group_server.id).status

    assert manager._cloud.delete_server(student_server.id)
    assert manager._cloud.delete_server(group_server.id)

    test_remove_course()


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
