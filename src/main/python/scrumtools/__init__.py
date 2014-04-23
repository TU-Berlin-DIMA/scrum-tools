from scrumtools import base, github, trello, error

VERSION = (0, 0, 1)

get_version = lambda: '.'.join(map(str, VERSION))

__all__ = [ 'base', 'github', 'trello', 'error' ]