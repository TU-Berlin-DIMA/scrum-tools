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
import json
import sys

import requests
from requests.exceptions import RequestException
from cement.core import controller
from termcolor import cprint, colored
from trello import TrelloApi

from scrumtools import data, error


try:
    prompt = raw_input
except NameError:
    prompt = input


class TrelloController(controller.CementBaseController):
    class Meta:
        label = 'trello'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "A set of batch management tools for Trello."

        config_section = 'trello'
        config_defaults = dict(
            auth_key=None,
            auth_token=None,
            organization='example.org',
            board_admins='example',
            board_pattern='example.g%02d',
            board_admins_group=0,
            board_lists=['Product Backlog', 'To Do', 'Doing', 'Done'],
        )

        arguments = [
            (['-U', '--users-file'],
             dict(action='store', metavar='FILE', dest='users_file',
                  help='a CSV file listing all users')),
            (['-O', '--organization'],
             dict(action='store', metavar='NAME', dest='organization',
                  help='the organization managing the Trello repositories')),
            (['-C', '--card-name'],
             dict(action='store', metavar='NAME', dest='card_name',
                  help='name of a card to be added')),
            (['-D', '--card-description'],
             dict(action='store', metavar='NAME', dest='card_description', default=None,
                  help='description of a card to be added')),
            (['-L', '--card-list'],
             dict(action='store', metavar='NAME', dest='card_list', default='Product Backlog',
                  help='name of the list (in all boards) to add this card to')),
        ]

    @controller.expose(hide=True)
    def default(self):
        self.app.args.parse_args(['--help'])

    @controller.expose(help="Authorizes scrum-tools with a Trello account.")
    def authorize(self):
        self.app.log.debug('Authorizing a Trello user.')

        # validate required config parameters
        if not self.app.config.get('trello', 'auth_key'):
            raise error.ConfigError("Missing config parameter 'trello.auth_key'! "
                                    "Please run 'scrum-tools trello authorize' first! ")

        try:
            tl = TrelloApi(self.app.config.get('trello', 'auth_key'))
            url = tl.get_token_url('scrum-tools', expires='30days', write_access=True)

            cprint(os.linesep.join(["Please follow the link below and update these entries in the [trello] section "
                                    "of your scrum-tools config: ",
                                    "  auth_key = %s" % self.app.config.get('trello', 'auth_key'),
                                    "  auth_token = %s" % '<generated_token>']), 'green')
            cprint("URL: %s" % url, 'green')
        except RuntimeError as e:
            raise e

    @controller.expose(help="Validate the provided Trello account names.")
    def validate_users(self):
        self.app.log.debug('Validating Trello account names.')

        # validate required config parameters
        if not self.app.config.get('trello', 'auth_key') or not self.app.config.get('trello', 'auth_token'):
            raise error.ConfigError("Missing config parameter 'trello.auth_key' and/or 'trello.auth_token'! "
                                    "Please run 'scrum-tools trello authorize' first! ")

        key_id = self.app.config.get('core', 'users_schema_key_id')
        key_trello = self.app.config.get('core', 'users_schema_key_trello')

        # get the users
        user_repository = data.UserRepository(self.app.config)
        # create trello session
        tl = TrelloApi(self.app.config.get('trello', 'auth_key'), self.app.config.get('trello', 'auth_token'))

        for u in user_repository.users():
            if not u[key_trello]:
                cprint("Skipping empty Trello account for user '%s'." % u[key_id], 'yellow', file=sys.stdout)
                continue

            print colored("Validating Trello account '%s' for user '%s'..." % (u[key_trello], u[key_id]), 'green'),
            try:
                tl.members.get(u[key_trello])
                print colored('OK', 'green', attrs=['bold'])

            except RequestException:
                print colored('Not OK', 'red', attrs=['bold'])

    @controller.expose(help="Creates Trello boards.")
    def create_boards(self):
        self.app.log.debug('Creating Trello boards.')

        # validate required config parameters
        if not self.app.config.get('trello', 'auth_key') or not self.app.config.get('trello', 'auth_token'):
            raise error.ConfigError("Missing config parameter 'trello.auth_key' and/or 'trello.auth_token'! "
                                    "Please run 'scrum-tools trello authorize' first! ")

        # schema keys
        key_group = self.app.config.get('core', 'users_schema_key_group')
        key_trello = self.app.config.get('core', 'users_schema_key_trello')
        # organization
        organization = self.app.config.get('trello', 'organization')
        # boards setup
        board_admins_name = self.app.config.get('trello', 'board_admins')
        board_pattern = self.app.config.get('trello', 'board_pattern')
        board_lists = self.app.config.get('trello', 'board_lists')
        admins_group = self.app.config.get('trello', 'board_admins_group')

        # get the users
        user_repository = data.UserRepository(self.app.config)
        # create trello session
        tl = TrelloApi(self.app.config.get('trello', 'auth_key'), self.app.config.get('trello', 'auth_token'))

        # get the organization
        org = tl.organizations.get(organization)
        if not org:
            raise RuntimeError("Organization '%s' not found" % organization)

        # get all organization boards
        boards = dict((b['name'], b) for b in tl.organizations.get_board(organization))

        # create group boards
        for group in user_repository.groups():
            board_name = board_pattern % int(group)
            board_admins = set(u[key_trello] for u in user_repository.users(lambda x: x[key_group] == admins_group))
            board_members = set(u[key_trello] for u in user_repository.users(lambda x: x[key_group] == group))
            self.__create_board(tl, org, board_name, set(board_lists), board_admins, board_members, boards)

        # create admins board
        board_admins = set(u[key_trello] for u in user_repository.users(lambda x: x[key_group] == admins_group))
        board_members = set()
        self.__create_board(tl, org, board_admins_name, set(board_lists), board_admins, board_members, boards)

    @controller.expose(help="Creates Trello boards.")
    def create_card(self):
        self.app.log.debug('Creating Trello boards.')

        # validate required config parameters
        if not self.app.config.get('trello', 'auth_key') or not self.app.config.get('trello', 'auth_token'):
            raise error.ConfigError("Missing config parameter 'trello.auth_key' and/or 'trello.auth_token'! "
                                    "Please run 'scrum-tools trello authorize' first! ")

        if not self.app.pargs.card_name:
            raise error.ConfigError("Missing card name! Please set a '--card-name' option value!")

        # card parameters
        card_list = self.app.pargs.card_list
        card_name = self.app.pargs.card_name
        card_desc = self.app.pargs.card_description
        # organization
        organization = self.app.config.get('trello', 'organization')
        # boards setup
        board_pattern = self.app.config.get('trello', 'board_pattern')

        # get the users
        user_repository = data.UserRepository(self.app.config)
        # create trello session
        tl = TrelloApi(self.app.config.get('trello', 'auth_key'), self.app.config.get('trello', 'auth_token'))

        # get the organization
        org = tl.organizations.get(organization)
        if not org:
            raise RuntimeError("Organization '%s' not found" % organization)

        # get all user group boards
        board_names = [board_pattern % int(group) for group in user_repository.groups()]
        boards = [b for b in tl.organizations.get_board(organization) if b['name'] in board_names]

        # add new card to all boards
        for board in boards:
            # get lists for this board
            board_lists = dict([(l['name'], l) for l in tl.boards.get_list(board['id'])])

            # skip if given card list does not exist in board
            if not card_list in board_lists:
                print colored("Skipping board '%s' (no list found)..." % (board['name']), 'green', attrs=['bold']),
                continue

            print colored("Adding card to list '%s' in '%s'..." % (card_list, board['name']), 'green', attrs=['bold']),
            try:
                tl.cards.new(name=card_name, idList=[board_lists[card_list]['id']], desc=card_desc)
                print colored('OK', 'green', attrs=['bold'])
            except RequestException:
                print colored('Not OK', 'red', attrs=['bold'])

    def __add_board_member(self, board, member, member_type):
        p = dict(key=self.app.config.get('trello', 'auth_key'), token=self.app.config.get('trello', 'auth_token'))
        d = dict(type=member_type)

        print colored("Adding '%s' as %s member of '%s'..." % (member, member_type, board['name']),
                      'green', attrs=['bold']),
        try:
            resp = requests.put("https://trello.com/1/boards/%s/members/%s" % (board['id'], member), params=p, data=d)
            resp.raise_for_status()
            json.loads(resp.content)
            print colored('OK', 'green', attrs=['bold'])
        except RequestException:
            print colored('Not OK', 'red', attrs=['bold'])

    def __create_board(self, tl, org, board_name, board_lists, board_admins, board_members, boards):
        if not board_name in boards:
            print colored("Creating board '%s'..." % board_name, 'green'),

            try:
                board = tl.boards.new(name=board_name, idOrganization=org['id'])
                boards[board_name] = board
                print colored('OK', 'green', attrs=['bold'])
            except RequestException:
                print colored('Not OK', 'red', attrs=['bold'])
        else:
            print colored("Skipping board '%s' (already exists)." % board_name, 'yellow')

        board = boards[board_name]

        board_lists_curr = set(l['name'] for l in tl.boards.get_list(board['id']))

        print colored("Adding missing lists to board '%s'" % board_name, 'green', attrs=['bold'])
        for list_name in board_lists - board_lists_curr:
            print colored("Adding list '%s' to board '%s'..." % (list_name, board['name']), 'green', attrs=['bold']),
            try:
                tl.lists.new(list_name, board['id'])
                print colored('OK', 'green', attrs=['bold'])
            except RequestException:
                print colored('Not OK', 'red', attrs=['bold'])

        board_admins_curr = set([m['username'] for m in tl.boards.get_member_filter('admins', board['id'])])
        board_allmembers_curr = set([m['username'] for m in tl.boards.get_member_filter('all', board['id'])])

        print colored("Adding missing admins to board '%s'" % board_name, 'green', attrs=['bold'])
        for u in board_admins - board_admins_curr:
            self.__add_board_member(board, u, 'admin')

        print colored("Adding missing members to board '%s'" % board_name, 'green', attrs=['bold'])
        for u in board_members - board_allmembers_curr:
            self.__add_board_member(board, u, 'normal')