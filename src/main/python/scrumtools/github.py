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
from github3 import login, models
from scrumtools import data, error
from termcolor import cprint, colored
from cement.core import controller
from requests.exceptions import ConnectionError

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
            auth_id=None,
            auth_token=None,
            organization='example.org',
            team_admins='example.admins',
            team_admins_group=-1,
            team_users='example.users',
            team_pattern='example.g%02d',
            repo_admins='example',
            repo_users='example',
            repo_pattern='example.g%02d',
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

    @controller.expose(help="Authorizes scrum-tools with a GitHub account.")
    def authorize(self):
        self.app.log.debug('Authorizing a GitHub user.')

        (username, password) = self.__class__.prompt_login()
        try:
            gh = login(username, password, two_factor_callback=self.__class__.prompt_two_factor_login)
            au = gh.authorize(username,
                              password,
                              scopes=['repo', 'delete_repo', 'admin:org'],
                              note='Scrum-tools on %s' % socket.gethostname())

            cprint(os.linesep.join(["Please copy these lines into the [github] section of your scrum-tools config:",
                                    "  auth_id    = %s " % au.id,
                                    "  auth_token = %s " % au.token]), 'green')
        except (models.GitHubError, ConnectionError) as e:
            raise RuntimeError(e.msg)

    @controller.expose(help="Validate the provided GitHub account names.")
    def validate_users(self):
        self.app.log.debug('Validating GitHub account names.')

        # validate required config parameters
        if not self.app.config.get('github', 'auth_token') or not self.app.config.get('github', 'auth_id'):
            raise error.ConfigError("Missing config parameter 'github.auth_id' and/or 'github.auth_token'! "
                                    "Please run 'scrum-tools github authorize' first! ")

        key_id = self.app.config.get('core', 'users_schema_key_id')
        key_github = self.app.config.get('core', 'users_schema_key_github')

        user_repository = data.UserRepository(self.app.config)

        gh = login(token=self.app.config.get('github', 'auth_token'))

        for u in user_repository.users():
            if not u[key_github]:
                cprint("Skipping empty GitHub account for user '%s'." % u[key_id], 'yellow', file=sys.stdout)
                continue

            print colored("Validating GitHub account '%s' for user '%s'..." % (u[key_github], u[key_id]), 'green'),
            try:
                if gh.user(u[key_github]):
                    print colored('OK', 'green', attrs=['bold'])
                else:
                    raise RuntimeError("Github user '%s' not found" % u[key_github])
            except RuntimeError:
                print colored('Not OK', 'red', attrs=['bold'])

    @controller.expose(help="Creates GitHub repositories.")
    def create_repos(self):
        self.app.log.debug('Creating GitHub repositories.')

        # validate required config parameters
        if not self.app.config.get('github', 'auth_token') or not self.app.config.get('github', 'auth_id'):
            raise error.ConfigError("Missing config parameter 'github.auth_id' and/or 'github.auth_token'! "
                                    "Please run 'scrum-tools github authorize' first! ")

        # organization
        organization = self.app.config.get('github', 'organization')
        # teams setup
        team_admins = self.app.config.get('github', 'team_admins')
        team_users = self.app.config.get('github', 'team_users')
        team_pattern = self.app.config.get('github', 'team_pattern')
        # repos setup
        repo_admins = self.app.config.get('github', 'repo_admins')
        repo_users = self.app.config.get('github', 'repo_users')
        repo_pattern = self.app.config.get('github', 'repo_pattern')

        # get the users
        user_repository = data.UserRepository(self.app.config)
        # create github session
        gh = login(token=self.app.config.get('github', 'auth_token'))

        # get the organization
        org = gh.organization(organization)
        if not org:
            raise RuntimeError("Organization '%s' not found" % organization)

        # get all organization repos
        teams = dict((t.name, t) for t in org.iter_teams())
        repos = dict((r.name, r) for r in org.iter_repos())

        # create group repos
        for group in user_repository.groups():
            repo_group = repo_pattern % int(group)
            team_group = team_pattern % int(group)
            repo_teams = [v for (k, v) in teams.iteritems() if k in [team_group, team_admins]]
            self.__class__.__create_repo(org, repo_group, repo_teams, repos)

        # create admins repo
        repo_teams = [v for (k, v) in teams.iteritems() if k in [team_admins]]
        self.__class__.__create_repo(org, repo_admins, repo_teams, repos)

        # create users repo
        repo_teams = [v for (k, v) in teams.iteritems() if k in [team_admins, team_users]]
        self.__class__.__create_repo(org, repo_users, repo_teams, repos)

    @controller.expose(help="Deletes GitHub repositories.")
    def delete_repos(self):
        self.app.log.debug('Deleting GitHub repositories.')

        if not self.__class__.prompt_confirm(colored('This cannot be undone! Proceed? (yes/no): ', 'red')):
            cprint("Aborting delete command.", 'yellow', file=sys.stdout)
            return

        # validate required config parameters
        if not self.app.config.get('github', 'auth_token') or not self.app.config.get('github', 'auth_id'):
            raise error.ConfigError("Missing config parameter 'github.auth_id' and/or 'github.auth_token'! "
                                    "Please run 'scrum-tools github authorize' first! ")

        # organization
        organization = self.app.config.get('github', 'organization')
        # repos setup
        repo_admins = self.app.config.get('github', 'repo_admins')
        repo_users = self.app.config.get('github', 'repo_users')
        repo_pattern = self.app.config.get('github', 'repo_pattern')

        user_repository = data.UserRepository(self.app.config)

        gh = login(token=self.app.config.get('github', 'auth_token'))

        # get the organization
        org = gh.organization(organization)
        if not org:
            raise RuntimeError("Organization '%s' not found" % organization)

        # get all organization repos
        repos = dict((t.name, t) for t in org.iter_repos())

        # delete group repos
        for group in user_repository.groups():
            repo_name = repo_pattern % int(group)
            self.__class__.__delete_repo(repo_name, repos)

        # delete admins repo
        self.__class__.__delete_repo(repo_admins, repos)

        # delete users repo
        self.__class__.__delete_repo(repo_users, repos)

    @controller.expose(help="Creates GitHub teams.")
    def create_teams(self):
        self.app.log.debug('Creating GitHub teams.')

        # validate required config parameters
        if not self.app.config.get('github', 'auth_token') or not self.app.config.get('github', 'auth_id'):
            raise error.ConfigError("Missing config parameter 'github.auth_id' and/or 'github.auth_token'! "
                                    "Please run 'scrum-tools github authorize' first! ")

        # schema keys
        key_group = self.app.config.get('core', 'users_schema_key_group')
        key_github = self.app.config.get('core', 'users_schema_key_github')
        # organization
        organization = self.app.config.get('github', 'organization')
        # teams setup
        team_admins = self.app.config.get('github', 'team_admins')
        team_admins_group = self.app.config.get('github', 'team_admins_group')
        team_users = self.app.config.get('github', 'team_users')
        team_pattern = self.app.config.get('github', 'team_pattern')
        # repos setup
        repo_admins = self.app.config.get('github', 'repo_admins')
        repo_users = self.app.config.get('github', 'repo_users')
        repo_pattern = self.app.config.get('github', 'repo_pattern')

        # get the users
        user_repository = data.UserRepository(self.app.config)
        # create github session
        gh = login(token=self.app.config.get('github', 'auth_token'))

        # get the organization
        org = gh.organization(organization)
        if not org:
            raise RuntimeError("Organization '%s' not found" % organization)

        # get all organization teams
        teams = dict((t.name, t) for t in org.iter_teams())

        # create group teams
        for group in user_repository.groups():
            team_name = team_pattern % int(group)
            repo_names = ['%s/%s' % (organization, repo_pattern % int(group))]
            self.__class__.__create_team(org, team_name, repo_names, 'push', teams)

        # update group teams members
        for group in user_repository.groups():
            team = teams[team_pattern % int(group)]
            members_act = set(m.login for m in team.iter_members())
            members_exp = set(u[key_github] for u in user_repository.users(lambda x: x[key_group] == group))
            self.__class__.__update_team_members(team, members_act, members_exp)

        # create admins team
        repo_names = ['%s/%s' % (organization, repo_admins)] + \
                     ['%s/%s' % (organization, repo_users)] + \
                     ['%s/%s' % (organization, repo_pattern % int(group)) for group in user_repository.groups()]
        self.__class__.__create_team(org, team_admins, repo_names, 'admin', teams)

        # update admins team members
        team = teams[team_admins]
        members_act = set(m.login for m in team.iter_members())
        members_exp = set(u[key_github] for u in user_repository.users(lambda x: x[key_group] == team_admins_group))
        self.__class__.__update_team_members(team, members_act, members_exp)

        # create users team
        repo_names = ['%s/%s' % (organization, repo_users)]
        self.__class__.__create_team(org, team_users, repo_names, 'pull', teams)

        # update users team members
        team = teams[team_users]
        members_act = set(m.login for m in team.iter_members())
        members_exp = set(u[key_github] for u in user_repository.users())
        self.__class__.__update_team_members(team, members_act, members_exp)

    @controller.expose(help="Deletes GitHub teams.")
    def delete_teams(self):
        if not self.__class__.prompt_confirm(colored('This cannot be undone! Proceed? (yes/no): ', 'red')):
            cprint("Aborting delete command.", 'yellow', file=sys.stdout)
            return

        self.app.log.debug('Deleting GitHub teams.')

        # validate required config parameters
        if not self.app.config.get('github', 'auth_token') or not self.app.config.get('github', 'auth_id'):
            raise error.ConfigError("Missing config parameter 'github.auth_id' and/or 'github.auth_token'! "
                                    "Please run 'scrum-tools github authorize' first! ")

        # organization
        organization = self.app.config.get('github', 'organization')
        # teams setup
        team_admins = self.app.config.get('github', 'team_admins')
        team_users = self.app.config.get('github', 'team_users')
        team_pattern = self.app.config.get('github', 'team_pattern')

        user_repository = data.UserRepository(self.app.config)

        gh = login(token=self.app.config.get('github', 'auth_token'))

        # get the organization
        org = gh.organization(organization)
        if not org:
            raise RuntimeError("Organization '%s' not found" % organization)

        # get all organization teams
        teams = dict((t.name, t) for t in org.iter_teams())

        # delete group teams
        for group in user_repository.groups():
            team_name = team_pattern % int(group)
            self.__class__.__delete_team(team_name, teams)

        # delete admins team
        self.__class__.__delete_team(team_admins, teams)

        # delete users team
        self.__class__.__delete_team(team_users, teams)

    @staticmethod
    def __create_repo(org, repo_name, teams, repos):
        if not repo_name in repos:
            print colored("Creating repository '%s'..." % repo_name, 'green'),
            repo = org.create_repo(name=repo_name, private=True, has_wiki=False)
            if repo:
                repos[repo_name] = repo
                print colored('OK', 'green', attrs=['bold'])
            else:
                print colored('Not OK', 'red', attrs=['bold'])
        else:
            print colored("Skipping repository '%s' (already exists)." % repo_name, 'yellow')

        for team in teams:
            print "adding repo '%s/%s' to team %s" % (org.login, repo_name, team.name)
            team.add_repo('%s/%s' % (org.login, repo_name))

    @staticmethod
    def __delete_repo(repo_name, repos):
        if repo_name in repos:
            print colored("Deleting repository '%s'..." % repo_name, 'green'),
            if repos[repo_name].delete():
                del repos[repo_name]
                print colored('OK', 'green', attrs=['bold'])
            else:
                print colored('Not OK', 'red', attrs=['bold'])
        else:
            print colored("Skipping repository '%s' (does not exist)." % repo_name, 'yellow')

    @staticmethod
    def __create_team(org, team_name, repo_names, premission, teams):
        if not team_name in teams:
            print colored("Creating team '%s'..." % team_name, 'green'),
            team = org.create_team(name=team_name, repo_names=repo_names, permissions=premission)
            team.edit(team_name, permission=premission)  # bypass a bug in create_team
            if team:
                teams[team_name] = team
                print colored('OK', 'green', attrs=['bold'])
            else:
                print colored('Not OK', 'red', attrs=['bold'])
        else:
            print colored("Skipping team '%s' (already exists)." % team_name, 'yellow')

    @staticmethod
    def __delete_team(team_name, teams):
        if team_name in teams:
            print colored("Deleting team '%s'..." % team_name, 'green'),
            if teams[team_name].delete():
                del teams[team_name]
                print colored('OK', 'green', attrs=['bold'])
            else:
                print colored('Not OK', 'red', attrs=['bold'])
        else:
            print colored("Skipping team '%s' (does not exist)." % team_name, 'yellow')

    @staticmethod
    def __update_team_members(team, members_act, members_exp):
        print colored("Updating team members for team '%s'." % team.name, 'green')

        # add missing team members
        for u in members_exp - members_act:
            print colored("Adding '%s' to team '%s'..." % (u, team.name), 'green'),
            if team.add_member(u):
                print colored('OK', 'green', attrs=['bold'])
            else:
                print colored('Not OK', 'red', attrs=['bold'])

        # remove unexpected team members
        for u in members_act - members_exp:
            print colored("Removing '%s' from team '%s'..." % (u, team.name), 'green'),
            if team.remove_member(u):
                print colored('OK', 'green', attrs=['bold'])
            else:
                print colored('Not OK', 'red', attrs=['bold'])

    @staticmethod
    def prompt_login():
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
    def prompt_two_factor_login():
        code = ''
        while not code:
            code = prompt('Enter 2FA code: ')
        return code

    @staticmethod
    def prompt_confirm(question='Do you really want to do this (yes/no)?', answer_true='yes'):
        return prompt(question) == answer_true