import re
import os
import sys
import json
import time
import errno
import pickle
import logging
import functools
import subprocess
from collections import Iterable
logger = logging.getLogger(__name__)


def pickleObject(fullPath, toPickle):
    """ Pickle an object at the designated path """
    with open(fullPath, 'w') as f:
        pickle.dump(toPickle, f)
    f.close()


def unPickleObject(fullPath):
    """ unPickle an object from the designated file path """
    with open(fullPath, 'r') as f:
        fromPickle = pickle.load(f)
    f.close()
    return fromPickle


def jsonWrite(data, filePath):
    with open(filePath, 'w') as outfile:
        json.dump(data, outfile)


def jsonLoad(filePath):
    with open(filePath, 'r') as dataFile:
        return json.load(dataFile)


def getFirstItem(iterable, default=None):
    """Return the first item if any"""
    if iterable:
        for item in iterable:
            return item
    return default


def flatten(coll):
    """Flatten a list while keeping strings"""
    for i in coll:
        if isinstance(i, Iterable) and not isinstance(i, basestring):
            for subc in flatten(i):
                yield subc
        else:
            yield i


def string2bool(string, strict=True):
    """Convert a string to its boolean value.
    The strict argument keep the string if neither True/False are found
    """
    if not isinstance(string, basestring):
        return string
    if strict:
        return string == "True"
    else:
        if string == 'True':
            return False
        elif string == 'False':
            return True
        else:
            return string


def createDir(path):
    """Creates a directory"""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def formatPath(fileName, path='', prefix='', suffix=''):
    """ Create a complete path with a filename, a path and prefixes/suffixes
    /path/prefix_filename_suffix.ext"""
    path = os.path.join(path, "") # Delete ?
    if suffix:
        suffix = '_' + suffix
    if prefix:
        prefix = prefix + '_'
    fileName, fileExt = os.path.splitext(fileName)
    filePath = os.path.join(path, prefix + fileName + suffix + fileExt)
    return filePath


def normpath(path):
    """Fix some problems with Maya evals or some file commands needing double escaped anti-slash '\\\\' in the path in Windows"""
    return os.path.normpath(path).replace('\\', '/')


def camelCaseSeparator(label, separator=' '):
    """Convert a CamelCase to words separated by separator"""
    return re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r'%s\1' % separator, label)


def toNumber(s):
    """Convert a string to an int or a float depending of their types"""
    try:
        return int(s)
    except ValueError:
        return float(s)


def replaceExtension(path, ext):
    if ext and not ext.startswith('.'):
        ext = ''.join(['.', ext])
    return path.replace(os.path.splitext(path)[1], ext)


def humansize(nbytes):
    suffixes = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
    if nbytes == 0:
        return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def lstripAll(toStrip, stripper):
    if toStrip.startswith(stripper):
        return toStrip[len(stripper):]
    return toStrip


def rstripAll(toStrip, stripper):
    if toStrip.endswith(stripper):
        return toStrip[:-len(stripper)]
    return toStrip


def openfolder(path):
    if sys.platform == 'darwin':
        return subprocess.Popen(['open', '--', path])
    elif sys.platform == 'linux2':
        return subprocess.Popen(['xdg-open', '--', path])
    elif sys.platform == 'win32':
        path = path.replace('/', '\\')
        return subprocess.Popen(['explorer', path])







def withmany(method):
    """A decorator that iterate through all the elements and eval each one if a list is in input"""
    @functools.wraps(method)
    def many(many_foos):
        for foo in many_foos:
            yield method(foo)
    method.many = many
    return method


def memoizeSingle(f):
    """Memoization decorator for a function taking a single argument"""
    class memodict(dict):

        def __missing__(self, key):
            ret = self[key] = f(key)
            return ret
    return memodict().__getitem__


def memoizeSeveral(f):
    """Memoization decorator for functions taking one or more arguments"""
    class memodict(dict):

        def __init__(self, f):
            self.f = f

        def __call__(self, *args):
            return self[args]

        def __missing__(self, key):
            ret = self[key] = self.f(*key)
            return ret
    return memodict(f)


def elapsedTime(f):
    @functools.wraps(f)
    def elapsed(*args, **kwargs):
        start = time.time()
        result =  f(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(elapsed)
        return result
    return elapsed