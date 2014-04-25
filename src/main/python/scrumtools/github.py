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

import sys

from termcolor import cprint, colored
from cement.core import controller
# noinspection PyPackageRequirements
from github3 import login, models

from scrumtools import data, error


try:
    prompt = raw_input
except NameError:
    prompt = input


class GitHubController(controller.CementBaseController):
    class Meta:
        label = 'github'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "A set of batch management tools for GitHub."

        config_section = 'github'
        config_defaults = dict(
            github_key=None,
            github_secret=None,
            github_token=None,
        )

        arguments = [
            (['-U', '--users-file'],
             dict(action='store', metavar='FILE', dest='users_file',
                  help='a CSV file listing all users')),
            (['-S', '--users-schema'],
             dict(action='store', nargs='+', metavar='COLUMN', dest='users_schema',
                  help='column schema for the users CSV file')),
        ]

    @controller.expose(hide=True)
    def default(self):
        self.app.args.parse_args(['--help'])

    @controller.expose(help="Authenticates scrum-tools with a GitHub account.")
    def authenticate(self):
        self.app.log.debug('Authenticating a GitHub user.')

        # validate required config parameters
        if not self.app.config.get('github', 'github_key'):
            raise error.ConfigError("Missing config parameter 'github.github_key'!")
        if not self.app.config.get('github', 'github_secret'):
            raise error.ConfigError("Missing config parameter 'github.github_secret'!")

        (username, password) = self.__class__.__login_prompt()
        try:
            gh = login(username, password, two_factor_callback=self.__class__.two_factor_login_prompt)
            au = gh.authorize(username,
                              password,
                              client_id=self.app.config.get('github', 'github_key'),
                              client_secret=self.app.config.get('github', 'github_secret'),
                              scopes=['repo', 'admin:org'],
                              note='Access for scrum-tools client app.')

            cprint("GitHub access token: %s " % colored(au.token, attrs=['bold']), 'green', file=sys.stdout)
        except models.GitHubError as e:
            raise RuntimeError(e.msg)

    @controller.expose(help="Validate the provided GitHub account names.")
    def validate_users(self):
        user_repository = data.UserRepository(self.app.config)
        for user in user_repository.users():
            print "%s: [%50s] [%50s] %s %s" % (user['Group'],
                                               user['Github'],
                                               user['Trello'],
                                               user['Name'],
                                               user['Surname'])

    @controller.expose(help="Creates a bunch of GitHub repositories.")
    def create_repos(self):
        pass

    @staticmethod
    def __login_prompt():
        import getpass

        u = prompt("GitHub username [%s]: " % getpass.getuser())
        if not u:
            u = getpass.getuser()

        password_prompt = lambda: (getpass.getpass("GitHub password: "), getpass.getpass('GitHub password (again): '))

        p1, p2 = password_prompt()
        while p1 != p2:
            print('Passwords do not match. Try again')
            p1, p2 = password_prompt()

        return u, p1

    @staticmethod
    def two_factor_login_prompt():
        code = ''
        while not code:
            code = prompt('Enter 2FA code: ')
        return code