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
import json
import os
import pickle
import re
import sys

NAME = 'Spanish'
VERSION = '0.0.2-2'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(sys.argv[0])[-1]

USAGESTR = """{versionstr}
    Translate a single english word into spanish,
    or use a regex pattern to find english words and translate them.

    Usage:
        {script} -h | -v
        {script} (-c | -j) [-D]
        {script} <query> [-D] [-t | -r] [-s]

    Options:
        <query>       : Word to translate.
        -c,--create   : Create new pickle data from the original text file.
        -D,--debug    : Debug mode, shows extra information.
        -h,--help     : Show this help message.
        -j,--json     : Create new json data from the original text file.
        -r,--reverse  : Translate a spanish word instead.
        -s,--nosort   : Don't ever sort the results (faster).
        -t,--text     : Force using the original text file.
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
    # Create mode?
    if argd['--create'] or argd['--json']:
        return create_files(use_json=argd['--json'])

    searchtypes = {'english': 'spanish', 'spanish': 'english'}
    if argd['--reverse']:
        searchtype = 'english'
        if not os.path.exists(ES_PKL):
            print('\nSpanish data not found: {}'.format(ES_PKL))
            return 1
        search = partial(find_pickle, filename=ES_PKL)
    else:
        searchtype = 'spanish'
        if (not argd['--text']) and os.path.exists(ENG_PKL):
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
    # Rules for formatting (spanish to english has some long "words").
    wordrjust = 25
    trans_indent_maxlen = wordrjust + 3
    trans_indent = ' ' * trans_indent_maxlen
    trans_maxlen = 80 - trans_indent_maxlen

    starttime = datetime.now()
    found = 0
    try:
        for word, worddata in search(query, sort=(not argd['--nosort'])):
            found += 1
            wordfmt = word.rjust(wordrjust)
            transfmt = format_block(
                ', '.join(worddata[searchtype]),
                blocksize=trans_maxlen,
                prepend=trans_indent,
                lstrip=True,
                spaces=True)
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


def create_files(use_json=False):
    """ Recreate the pickle files, or create json files from the original text.
    """
    if use_json:
        datatype = 'JSON'
        fileext = '.json'
        filemode = 'w'
        dump = json.dump
        adapt = lambda d: {
            k: (list(v) if isinstance(v, set) else v)
            for k, v in d.items()
        }
    else:
        datatype = 'pickle'
        fileext = '.pkl'
        filemode = 'wb'
        dump = pickle.dump
        adapt = lambda d: d

    debug('Creating english data...')
    try:
        eng = {
            w: adapt(wdata)
            for w, wdata in find_text('.+', filename=ENG_TXT)
        }
    except InvalidFile as ex:
        print('\nUnable to read english data: {}\n{}'.format(ENG_TXT, ex))
        return 1

    engfile = 'english-to-spanish{}'.format(fileext)
    if os.path.exists(engfile):
        engfile = '{}.new'.format(engfile)
    debug('Writing english file: {}'.format(engfile))
    try:
        with open(engfile, filemode) as feng:
            dump(eng, feng)
    except Exception as ex:
        print('\nFailed to create english {} data: {}'.format(datatype, ex))
        return 1
    else:
        print('\nCreated english data: {}'.format(engfile))

    debug('Creating spanish data...')
    es = eng_to_es(eng)
    if use_json:
        es = {k: adapt(v) for k, v in es.items()}
    esfile = 'spanish-to-english{}'.format(fileext)
    if os.path.exists(esfile):
        esfile = '{}.new'.format(esfile)
    debug('Writing spanish file: {}'.format(esfile))
    try:
        with open(esfile, filemode) as fes:
            dump(es, fes)
    except Exception as ex:
        print('\nFailed to create spanish {} data: {}'.format(datatype, ex))
        return 1
    else:
        print('\nCreated spanish data: {}'.format(esfile))

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


def eng_to_es(data):
    """ Transform the english data to spanish data, for when the english
        version changes. This is only used in development.
    """
    transformed = {}
    for word, wdata in data.items():
        for spanish in wdata['spanish']:
            if transformed.get(spanish, None):
                transformed[spanish]['english'].add(word)
            else:
                transformed[spanish] = {
                    'english': {word},
                    'pronounce': wdata['pronounce']
                }
    return transformed


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
        querypat = re.compile(query, re.IGNORECASE)
    except re.error as ex:
        raise InvalidQuery('Invalid query: {}\n    {}'.format(query, ex))

    clean = lambda w: re.sub('^\d{1,3}\.', '', w.strip())
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
                        word, pron = wordmatch.groups()
                        pron = pron.strip()
                        word = word.strip().lower()
                    else:
                        word = line.strip().lower()
                        pron = None
                    # Does this word match?
                    if querypat.search(word) is not None:
                        engword = word
                        indef = (
                            engword,
                            {'pronounce': pron, 'spanish': set()})
                    else:
                        engword = None
                        indef = None
                else:
                    # In spanish words.
                    if engword and indef:
                        spanish = line.strip()
                        if ',' in spanish:
                            spanish = (clean(s) for s in spanish.split(','))
                            indef[1]['spanish'].update(spanish)
                        else:
                            indef[1]['spanish'].add(clean(spanish))
    except EnvironmentError as ex:
        raise InvalidFile(str(ex)) from ex


def format_block(
        text,
        prepend=None, lstrip=False, blocksize=60,
        spaces=False, newlines=False):
    """ Format a long string into a block of newline seperated text. """
    lines = make_block(
        text,
        blocksize=blocksize,
        spaces=spaces,
        newlines=newlines)
    if prepend is None:
        return '\n'.join(lines)
    if lstrip:
        # Add 'prepend' before each line, except the first.
        return '\n{}'.format(prepend).join(lines)
    # Add 'prepend' before each line.
    return '{}{}'.format(prepend, '\n{}'.format(prepend).join(lines))


def make_block(text, blocksize=60, spaces=False, newlines=False):
    """ Turns a long string into a list of lines no greater than 'blocksize'
        in length. This can wrap on spaces, instead of chars if wrap_spaces
        is truthy.
    """
    if not spaces:
        # Simple block by chars.
        return (text[i:i + blocksize] for i in range(0, len(text), blocksize))
    if newlines:
        # Preserve newlines
        lines = []
        for line in text.split('\n'):
            lines.extend(make_block(line, blocksize=blocksize, spaces=True))
        return lines

    # Wrap on spaces (ignores newlines)..
    words = text.split()
    lines = []
    curline = ''
    for word in words:
        possibleline = ' '.join((curline, word)) if curline else word

        if len(possibleline) > blocksize:
            lines.append(curline)
            curline = word
        else:
            curline = possibleline
    if curline:
        lines.append(curline)
    return lines


def remove_junk(data):
    """ Removes junk numbers from spanish words. This is only used in
        development, data updates.
    """
    fixed = {}
    for word, wdata in data.items():
        fixed[word] = {'pronounce': wdata['pronounce'], 'spanish': set()}
        for spanish in wdata['spanish']:
            fixed[word]['spanish'].add(re.sub('^\d{1,3}\.', '', spanish))
    return fixed


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
