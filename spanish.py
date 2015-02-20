#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" spanish.py
    ...Shows spanish/english translations. Uses pickled data if available,
    but falls back to the original text file if needed.
    -Christopher Welborn 03-23-2014
"""

from datetime import datetime
from docopt import docopt
from functools import partial
import inspect
import os
import pickle
import re
import sys

NAME = 'Spanish'
VERSION = '0.0.2-1'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(sys.argv[0])[-1]

USAGESTR = """{versionstr}
    Translate a single english word into spanish,
    or use a regex pattern to find english words and translate them.

    Usage:
        {script} -h | -v
        {script} [-D] [-r] [-s] <query>

    Options:
        <query>       : English word to translate.
        -D,--debug    : Debug mode, shows extra information.
        -h,--help     : Show this help message.
        -r,--reverse  : Spanish word to translate.
        -s,--nosort   : Don't ever sort the results (faster).
        -v,--version  : Show version.
""".format(script=SCRIPT, versionstr=VERSIONSTR)

ENG_TXT = os.path.join(sys.path[0], 'english-to-spanish.txt')
ENG_PKL = os.path.join(sys.path[0], 'english-to-spanish.pkl')
ES_PKL = os.path.join(sys.path[0], 'spanish-to-english.pkl')


def main(argd):
    """ Main entry point, expects doctopt arg dict as argd """
    global debug
    if not argd['--debug']:
        debug = dummy

    searchtypes = {'english': 'spanish', 'spanish': 'english'}
    if argd['--reverse']:
        searchtype = 'english'
        if not os.path.exists(ES_PKL):
            print('\nSpanish data not found: {}'.format(ES_PKL))
            return 1
        search = partial(find_pickle, filename=ES_PKL)
    else:
        searchtype = 'spanish'
        if os.path.exists(ENG_PKL):
            search = partial(find_pickle, filename=ENG_PKL)
        elif os.path.exists(ENG_TXT):
            search = partial(find_text, filename=ENG_TXT)
        else:
            print('\nEnglish data not found: {}'.format(
                '    {}'.format('\n    '.join((ENG_PKL, ENG_TXT)))
            ))
            return 1

    query = argd['<query>'].lower()
    print('Searching for: {}'.format(query))
    print('...{} to {}\n'.format(searchtypes[searchtype], searchtype))
    starttime = datetime.now()
    found = 0
    try:
        for word, worddata in search(query, sort=(not argd['--nosort'])):
            found += 1
            wordfmt = word.rjust(20)
            transfmt = '; '.join(worddata[searchtype])
            print('{} : {}'.format(wordfmt, transfmt))
    except (InvalidFile, InvalidQuery) as excancel:
        print('\n{}'.format(excancel))
        return 1
    except KeyboardInterrupt:
        print('\nUser cancelled.\n')
        return 1
    except Exception as ex:
        print('\nError during search:\n{}'.format(ex))
        return 1
    finally:
        # Print stats.
        translbl = 'translation' if found == 1 else 'translations'
        print('\nFound {} {} for: {}'.format(found, translbl, argd['<query>']))
        print('({}s)'.format(duration_str(starttime)))
    return 0


def debug(*args, **kwargs):
    """ Print a debug message. """
    if not args:
        args = ['']
    # Get filename, line number, and function name.
    frame = inspect.currentframe()
    frame = frame.f_back
    fname = os.path.split(frame.f_code.co_filename)[-1]
    lineno = frame.f_lineno
    func = frame.f_code.co_name
    # Patch args to stay compatible with print().
    pargs = list(args)
    lineinfo = '{}:{} {}(): '.format(fname, lineno, func).ljust(40)
    pargs[0] = ''.join((lineinfo, pargs[0]))

    print(*pargs, **kwargs)


def dummy(*args, **kwargs):
    return None


def duration_str(starttime):
    """ Return time-elapsed in string format. """
    secs = (datetime.now() - starttime).total_seconds()
    return '{:0.2f}'.format(secs)


def ensure_files(*args):
    """ Ensure that all arguments are existing file paths. """
    for path in args:
        if not os.path.exists(path):
            print('Can\'t find: {}'.format(path))
            return False
    return True


def find_pickle(query, filename=None, sort=False):
    """ Search an existing pickled dict. """
    debug('Pickle mode, using file: {}'.format(filename))
    try:
        querypat = re.compile(query)
    except re.error as ex:
        raise InvalidQuery('Invalid query: {}\n    {}'.format(query, ex))
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
    except Exception:
        raise InvalidFile('Error reading data from: {}\n{}'.format(
            filename,
            ex))
    if sort:
        # Sorted search (slower)
        for word in sorted(data):
            if querypat.search(word):
                yield (word, data[word])
    else:
        for word, wdata in data.items():
            if querypat.search(word):
                yield (word, wdata)


def find_text(query, filename=None, sort=None):
    """ Search the original text file. """
    debug('Text mode, using file: {}'.format(filename))
    try:
        querypat = re.compile(query)
    except re.error as ex:
        raise InvalidQuery('Invalid query: {}\n    {}'.format(query, ex))

    indef = None
    engword = None
    # Parse english word lines.
    defpat = re.compile(r'(.+)(\[.+\])')
    try:
        with open(filename, 'r') as fin:
            for line in fin:
                if not line.strip():
                    # Skip blank lines.
                    continue
                if not line.startswith(' '):
                    # English word
                    # Yield last english word set.
                    if indef and engword:
                        yield indef
                    # Parse word/word-def
                    wordmatch = defpat.search(line)
                    if wordmatch is not None:
                        # Set new word basic info..
                        word, pron = defpat.search(line).groups()
                        pron = pron.strip()
                        word = word.strip().lower()
                    else:
                        word = line.strip().lower()
                        pron = None
                    # Does this word match?
                    if querypat.search(word) is not None:
                        engword = word
                        indef = (engword, {'pronounce': pron, 'spanish': []})
                    else:
                        engword = None
                        indef = None
                else:
                    # In spanish words.
                    if engword and indef:
                        spanish = line.strip().lower()
                        # Don't add duplicate words (the db has dupes)
                        if spanish not in indef[1]['spanish']:
                            indef[1]['spanish'].append(spanish)
    except EnvironmentError as ex:
        raise InvalidFile(str(ex)) from ex


class InvalidFile(Exception):

    """ Raised in find_pickle() if the pickle file can't be loaded. """
    pass


class InvalidQuery(Exception):

    """ Raised in find_text() and find_pickle()
        if the regex query can't be compiled.
    """
    pass

if __name__ == '__main__':
    mainret = main(docopt(USAGESTR, version=VERSIONSTR))
    sys.exit(mainret)
