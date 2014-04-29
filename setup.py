from setuptools import setup

setup(
    name='scrum-tools',
    version='0.1.0',
    author=u'Alexander Alexandrov',
    author_email='alexander.alexandrov@tu-berlin.de',
    packages=['scrumtools'],
    package_dir={'': 'src/main/python'},
    scripts=['src/main/scripts/scrum-tools'],
    install_requires=[
        'argcomplete>=0.8.0',  # Argcomplete argument completion
        'cement>=2.2',  # Cement CLI application framework
        'github3.py>=0.8.2',  # Github API client
        'termcolor>=1.1.0',  # Termcolor colored terminal
        'trello>=0.9.1',  # Trello API client
    ],
    url='https://github.com/TU-Berlin-DIMA/scrum-tools',
    license='Apache v2 Licence, see LICENCE file',
    description='A set of CLI tools for batch management of Scrum infrastructure (GitHub, Trello).',
    long_description=open('README.md').read(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Topic :: Software Development',
    ]
)