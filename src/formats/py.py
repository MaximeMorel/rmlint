#!/usr/bin/env python3
# encoding: utf-8

""" This file is part of rmlint.

rmlint is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

rmlint is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with rmlint.  If not, see <http://www.gnu.org/licenses/>.

uthors:

- Christopher <sahib> Pahl 2010-2014 (https://github.com/sahib)
- Daniel <SeeSpotRun> T.   2014-2014 (https://github.com/SeeSpotRun)
"""

# This is the python remover utility shipped inside the rmlint binary.
# The 200 lines source presented below is meant to be clean and hackable.
# It is intented to be used for corner cases where the built-in sh formatter
# is not enough or as an alternative to it. By default it works the same.

import os
import sys
import pwd
import json
import shutil
import argparse
import subprocess


def handle_duplicate_dir(path, original, **kwargs):
    shutil.rmtree(path)


def handle_duplicate_file(path, original, **kwargs):
    os.remove(path)


def handle_empty_dir(path, **kwargs):
    os.rmdir(path)


def handle_empy_file(path, **kwargs):
    os.remove(path)


def handle_nonstripped(path, **kwargs):
    subprocess.call(["strip", "--strip-debug", path])


def handle_badlink(path, **kwargs):
    os.remove(path)


CURRENT_UID = os.geteuid()
CURRENT_GID = pwd.getpwuid(CURRENT_UID).pw_gid


def handle_baduid(path, **kwargs):
    os.chmod(path, CURRENT_UID, -1)


def handle_badgid(path, **kwargs):
    os.chmod(path, -1, CURRENT_GID)


def handle_badugid(path, **kwargs):
    os.chmod(path, CURRENT_UID, CURRENT_GID)


OPERATIONS = {
    "duplicate_dir": handle_duplicate_dir,
    "duplicate_file": handle_duplicate_file,
    "emptydir": handle_empty_dir,
    "emptyfile": handle_empy_file,
    "nonstripped": handle_nonstripped,
    "badlink": handle_badlink,
    "baduid": handle_baduid,
    "badgid": handle_badgid,
    "badugid": handle_badugid,
}

MESSAGES = {
    "duplicate_dir": "removing tree",
    "duplicate_file": "removing",
    "emptydir": "removing",
    "emptyfile": "removing",
    "nonstripped": "stripping",
    "badlink": "removing",
    "baduid": "changing uid",
    "badgid": "changing gid",
    "badugid": "changing uid & gid",
}

USE_COLOR = sys.stdout.isatty() and sys.stderr.isatty()
COLORS = {
    'red':    "\x1b[31;01m" if USE_COLOR else "",
    'yellow': "\x1b[33;01m" if USE_COLOR else "",
    'reset':  "\x1b[0m" if USE_COLOR else "",
    'green':  "\x1b[32;01m" if USE_COLOR else "",
    'blue':   "\x1b[34;01m" if USE_COLOR else ""
}


def exec_operation(item, original=None):
    try:
        OPERATIONS[item['type']](item['path'], original=original, item=item)
    except OSError as err:
        print(
            '{c[red]}#{c[reset]} Error on `{item[path]}`:\\n{c[red]}#{c[reset]}    {err}'.format(
                item=item, err=err, c=COLORS
            ),
            file=sys.stderr
        )


def main(args, header, data, footer):
    seen_cksums = set()
    last_original_item = None

    for item in data:
        if item['type'].startswith('duplicate_') and item['is_original']:
            print(
                "\\n{c[green]}#{c[reset]} Deleting twins of {item[path]} ".format(
                    item=item, c=COLORS
                )
            )
            last_original_item = item

            # Do not handle originals.
            continue

        if not args.dry_run:
            exec_operation(item, original=last_original_item)

        print('{c[blue]}#{c[reset]} Handling ({t} -> {v}): {p}'.format(
            c=COLORS, t=item['type'], v=MESSAGES[item['type']], p=item['path'])
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Handle the files stored in rmlints json output'
    )

    parser.add_argument(
        'json_docs', metavar='json_doc', type=open, nargs='*',
        help='A json output of rmlint to handle (can be given many times)'
    )
    parser.add_argument(
        '-n', '--dry-run', action='store_true',
        help='Only print what would be done.'
    )
    parser.add_argument(
        '-a', '--no-ask', action='store_true', default=False,
        help='ask for confirmation before running (does nothing for -n)'
    )

    try:
        args = parser.parse_args()
    except FileNotFoundError as err:
        print(err)
        sys.exit(-1)

    if not args.json_docs:
        # None given on the commandline
        try:
            args.json_docs.append(open('.rmlint.json', 'r'))
        except FileNotFoundError as err:
            print('Cannot load default json document: ', str(err), file=sys.stderr)
            sys.exit(-2)

    json_docus = [json.load(doc) for doc in args.json_docs]
    json_elems = [item for sublist in json_docus for item in sublist]

    try:
        if not args.no_ask and not args.dry_run:
            print('\\nPlease hit any key before continuing to shredder your data.', file=sys.stderr)
            sys.stdin.read(1)

        for json_doc in json_docus:
            head, *data, footer = json_doc
            main(args, head, data, footer)

        if args.dry_run:
            print(
                '\\n{c[green]}#{c[reset]} This was a dry run. Nothing modified.'.format(
                    c=COLORS
                )
            )
    except KeyBoardInterrupt:
        print('canceled.')
