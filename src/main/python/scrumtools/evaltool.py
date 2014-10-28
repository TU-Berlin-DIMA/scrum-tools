"""
Copyright 2010-2014 DIMA Research Group, TU Berlin

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created on Apr 13, 2014
"""

from __future__ import absolute_import

import os
import sys
import socket

# noinspection PyPackageRequirements
from scrumtools import data, error
from termcolor import cprint, colored
from cement.core import controller

try:
    prompt = raw_input
except NameError:
    prompt = input


class EvalToolController(controller.CementBaseController):
    class Meta:
        label = 'evaltool'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "A set of batch management tools for the DIMA Evaluation Tool."

        config_section = 'evaltool'
        config_defaults = dict(
            course_id='1000',
            group_pattern='example.g%02d',
        )

        arguments = [
            (['-U', '--users-file'],
             dict(action='store', metavar='FILE', dest='users_file',
                  help='a CSV file listing all users')),
            (['-O', '--organization'],
             dict(action='store', metavar='NAME', dest='organization',
                  help='the organization managing the GitHub repositories')),
        ]

    @controller.expose(hide=True)
    def default(self):
        self.app.args.parse_args(['--help'])

    @controller.expose(help="Dump SQL code for groups.")
    def dump_sql_groups(self):
        self.app.log.debug('Dumping SQL code for groups.')

        # schema keys
        key_group = self.app.config.get('core', 'users_schema_key_group')
        key_github = self.app.config.get('core', 'users_schema_key_github')
        # groups setup
        course_id = int(self.app.config.get('evaltool', 'course_id'))
        group_pattern = self.app.config.get('evaltool', 'group_pattern')

        user_repository = data.UserRepository(self.app.config)

        print colored("-- Groups", 'green')
        for group in user_repository.groups():
            group_name = group_pattern % int(group)
            print colored("INSERT INTO GROUPS(id, group_name, course_id) VALUES (%d, '%s', %d);" % (course_id * 1000 + int(group), group_name, course_id), 'green')

        print colored("-- Group Authorities", 'green')
        for group in user_repository.groups():
            print colored("INSERT INTO GROUP_AUTHORITIES(group_id, authority) values (%d, 'ROLE_USER');" % (course_id * 1000 + int(group)), 'green')

        print colored("-- Group Members", 'green')
        for group in user_repository.groups():
            print colored("-- Group %02d" % int(group), 'green')
            for u in user_repository.users(lambda x: x[key_group] == group):
                print colored("INSERT INTO GROUP_MEMBERS(group_id, username) values (%d, '%s');" % (course_id * 1000 + int(group), u[key_github]), 'green')

    @controller.expose(help="Dump SQL code for users.")
    def dump_sql_users(self):
        self.app.log.debug('Dumping SQL code for users.')

        # schema keys
        key_id = self.app.config.get('core', 'users_schema_key_id')
        key_github = self.app.config.get('core', 'users_schema_key_github')

        user_repository = data.UserRepository(self.app.config)

        print colored("-- Users", 'green')
        for u in user_repository.users():
            if not u[key_github]:
                cprint("Skipping empty GitHub account for user '%s'." % u[key_id], 'yellow', file=sys.stdout)
                continue

            print colored("INSERT INTO USERS(username, password, enabled) VALUES ('%s', md5('%s{%s}'), true);" % (u[key_github], u[key_id], u[key_github]), 'green')