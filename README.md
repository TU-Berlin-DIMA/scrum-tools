scrum-tools
===========

A set of tools for batch management of Scrum infrastructure.

Provides simple wrappers for mass management of:

 * code repositories on [Github](https://github.com);
 * boards and cards on [Trello](https://trello.com).

Installation
------------

Using [PIP](https://pypi.python.org/pypi/pip):

``` bash
pip install scrum-tools
```

Usage
-----

Create a config file named `.scrum-settings.conf` in your `$HOME` folder. Here is a sample config file that you can use as a start:

```ini
[core]
users_file                    = /path/to/users.csv
users_file_skip_first         = true
users_file_delimiter          = ;
users_file_escape_char        =
users_schema                  = ID;Username;Name;Surname;E-Mail;Group;Github;Trello
users_schema_key_id           = ID
users_schema_key_username     = Username
users_schema_key_group        = Group
users_schema_key_github       = Github
users_schema_key_trello       = Trello

[github]
auth_id                       = 
auth_token                    = 
organization                  = TU-Berlin-DIMA
team_admins                   = IMPRO-3.SS14.Admins
team_admins_group             = 0
team_users                    = IMPRO-3.SS14.Users
team_pattern                  = IMPRO-3.SS14.G%02d
repo_admins                   = IMPRO-3.SS14.Admins
repo_users                    = IMPRO-3.SS14
repo_pattern                  = IMPRO-3.SS14.G%02d

[trello]
auth_key                      = 8cfa18b4d674cba889c466680f4d06d7
auth_token                    = 
organization                  = impro3ss14
board_admins                  = IMPRO-3.SS14.Admins
board_pattern                 = IMPRO-3.SS14.G%02d
board_admins_group            = 0
board_lists                   = Product Backlog;To Do;Doing;Done

[evaltool]
course_id                     = 1000 
group_pattern                 = IMPRO-3.SS14.G%02d
```

You gen then get the list of the available commans like this:

```bash
$ scrum-tools
```

In order to get access to the GitHub and Trello APIs, you need to authorize the `scrum-tools` app as an API client. Type

```bash
$ scrum-tools github authorize
$ scrum-tools github authorize
```

and update the `auth_*` parameters under the `[github]` and `[trello]` sections in your `.scrum-settings.conf` file accordingly.

Before issuing batch-management commands, you may want to validate the account names provided in your `users_file`:

```bash
$ scrum-tools github validate-users
$ scrum-tools github validate-users
```

You can create the corresponding project structure with the following commands:

```bash
$ # for Github
$ scrum-tools github create-teams  # creates group, users and admin teams
$ scrum-tools github create-repos  # creates group, users and admin repos
$ # for Trello
$ scrum-tools trello create-boards # creates group boards
```

You can also create a Trello card accross all Trello boards like that:

```bash
$ scrum-tools trello create-card \
>   --card-list="Backlog"
>   --card-name="Initialize your project!"
>   --card-description="Create and push an initial project structure at GitHub!"
```
