Spanish
=======

This is a spanish/english translation tool for the command line. It can be
used for quick lookups for spanish to english, or english to spanish.


Usage:
------

```
Usage:
    spanish -h | -v
    spanish (-c | -j) [-D]
    spanish <query> [-D] [-t | -r] [-s]

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
```

Examples:
--------

Look up the spanish word for 'high':
```
spanish high
```

Results:
```
            high : alto
       high tide : plemear
   super highway : autovía
           thigh : muslo
```

Look up the english word for 'alto':
```
spanish -r alto
```

Results:
```
            alto : lofty; contralto; high; contralto voice; loud; tall
         asfalto : asphalt
         basalto : basalt; whimstone
           salto : jump; leap
```

Dependencies:
-------------

It uses [docopt](http://docopt.org) to parse command-line arguments.
You can install it with [pip](https://pip.pypa.io/en/latest/installing.html):
```
pip install docopt
```

Notes:
------

I recommend creating a symlink to this somewhere in your `$PATH`:
```
ln -s /path/to/spanish.py ~/.local/bin/spanish
```

Compatibility:
--------------

This uses a couple Python 3 features that won't run as is using Python 2.
Porting it over would be easy but I see no reason to do so. If you'd like to
do it and need guidance let me know.

