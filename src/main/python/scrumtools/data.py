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

import csv
import codecs
import cStringIO


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """

    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class UserRepository:
    def __init__(self, config):
        # CSV file config
        self.__file = config.get('core', 'users_file')
        self.__file_delimiter = config.get('core', 'users_file_delimiter')
        self.__file_quotechar = config.get('core', 'users_file_escape_char')
        self.__file_skip_first = config.getboolean('core', 'users_file_skip_first')
        # CSV schema config
        self.__schema = config.get('core', 'users_schema')
        self.__key_group = config.get('core', 'users_schema_key_group')
        self.__key_id = config.get('core', 'users_schema_key_id')
        self.__key_github = config.get('core', 'users_schema_key_github')
        self.__key_trello = config.get('core', 'users_schema_key_trello')

        # sanitize input
        self.__file_quotechar = self.__file_quotechar if self.__file_quotechar else None
        self.__file_delimiter = self.__file_delimiter if self.__file_delimiter else None

        # read users from CSV file
        self.__users = [u for u in self.__read()]
        self.__users.sort(key=lambda x: x[self.__key_group])

        # create groups
        self.__groups = sorted(set([u[self.__key_group] for u in self.__users if u[self.__key_group] != '']))

    def users(self, f=None):
        for u in self.__users:
            if not f:
                yield u
            elif f(u):
                yield u

    def groups(self):
        for g in self.__groups:
            yield g

    def __read(self):
        with open(self.__file, 'rb') as f:
            reader = UnicodeReader(f, encoding='utf-8',
                                   delimiter=self.__file_delimiter,
                                   quoting=csv.QUOTE_NONE if not self.__file_quotechar else csv.QUOTE_MINIMAL,
                                   quotechar=self.__file_quotechar,
                                   skipinitialspace=True)

            if self.__file_skip_first:
                next(reader)

            for user in reader:
                if len(user) - len(self.__schema) == 1 and not user[-1]:
                    user = user[:-1]
                if len(user) - len(self.__schema) != 0:
                    raise ValueError("Expected CSV line with %d entries, got %d" % (len(self.__schema), len(user)))
                yield dict(zip(self.__schema, [field.strip() for field in user]))