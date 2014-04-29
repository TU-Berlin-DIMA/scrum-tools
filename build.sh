#!/bin/bash

python setup.py bdist_egg upload --identity="Alexander Alexandrov" --sign --quiet
python setup.py bdist_wininst --target-version=2.4 register upload --identity="Alexander Alexandrov" --sign --quiet
python setup.py sdist upload --identity="Alexander Alexandrov" --sign
