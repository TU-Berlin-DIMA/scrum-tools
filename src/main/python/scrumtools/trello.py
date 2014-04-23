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

from cement.core import controller


class TrelloController(controller.CementBaseController):
    class Meta:
        label = 'trello'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "A set of batch management tools for Trello."

        config_defaults = dict(
        )

        arguments = [
        ]

    @controller.expose(hide=True)
    def default(self):
        self.app.args.parse_args(['--help'])

    @controller.expose(help="Authenticates scrum-tools with a Trello account.")
    def authenticate(self):
        self.app.log.info('Authenticating a Trello user.')

    @controller.expose(help="Creates a bunch of Trello organizations.")
    def create(self):
        self.app.log.info("Inside trello.create function.")

    @controller.expose(help="Adds a Trello board to each organization.")
    def add_board(self):
        self.app.log.info("Inside trello.add_board function.")