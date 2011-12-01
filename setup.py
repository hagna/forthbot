#!/usr/bin/env python

from distutils.core import setup
from subprocess import Popen, PIPE
from twisted.python.filepath import FilePath
import sys, os


# for supporting versioning a release with the git tag
def call_git_describe(abbrev=4):
    try:
        cmd = FilePath(__file__).sibling('version.sh')
        if cmd.exists():
            p = Popen([cmd.path],
                  stdout=PIPE, stderr=PIPE)
        else:
            p = Popen(['git', 'describe', '--abbrev=%d' % abbrev],
                  stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        return line.strip()

    except Exception, e:
        print e
        return None

def read_release_version():
    try:
        rv = FilePath(__file__).sibling('forthbot').child('version.py')
        return rv.getContent().split('=')[1].strip()[1:-1]
    except:
        return None


def write_release_version(version):
    rv = FilePath(__file__).sibling('forthbot').child('version.py')
    rv.setContent('__version__ = "' + str(version) + '"')


def get_git_version(abbrev=4):
    release_version = read_release_version()
    version = call_git_describe(abbrev)
    if version is None:
        version = release_version
    if version is None:
        raise ValueError("Cannot find the version number!")
    if version != release_version:
        write_release_version(version)
    return version


# for installing the twisted plugin in the right place
data_files = []
data_files.append((os.path.join('twisted', 'plugins'), [os.path.join('twisted', 'plugins', 'bot.py')]))
print data_files

setupdict = dict(name='forthbot',
      version=get_git_version(),
      description='forthbot',
      author_email='not_telling',
      packages=['forthbot',],
      package_dir={'forthbot': 'forthbot'},
      package_data={'forthbot':['twisted/plugins/bot.py']},
     )



setup(**setupdict)
