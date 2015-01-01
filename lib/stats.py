"""
This tool allows you to record events and time their execution.

Initialize it one time with the name of the tool, the author and the number version:
stats = Stats('Toolname', 'author', 'b153') 
It will then process all the important info once and for all (datetime, username, software, project, machine name).
Then each time you want to record an event you call it back with the name of the status you want. 
For example each time you want to know a user opened your tool, call it :
stats.emit('open')

If you want to record the time the even took, you have to specify you want a timer by adding the 'True' argument behind the status. It will keep tracking of the event in case it crashes so if you want to know if the even is crashing and have no interest about the timer value, you can use that.
event = stats.emit('exec', True)
# some code here
event.stop()
You can call the event.stop() even if you didn't specified you wanted a timer, but it will not track if the event crashed during the execution then.



The main object 'Stats' fot for arguments: toolname (string), author (string), version (string)
It will then call the Row object through its emit() method with those arguments: status (string), timer (boolean, optional).
The Row object calls the Datetimer object to keep track of the current date and time, and to get the elapsed time.



It records everything in a table specific to the soft used. If the soft can't be retrieved it is recorded in the 'Unknown' table. You can blacklist users so the records go in another specific table. 
Timeouts to the database are handled. If a table does not exists, it will be created automatically. And if everything fails to insert the data in the database, it is saved in a file on the network with the SQL call with a specific uuid.
The calls to the database are threaded (and locked) so they won't block the execution of the main programs.

The crashes are tracked by putting '0.00000' in the timer field, then it is updated when the event finish. If the event has crashed, the timer will still be at '0.00000'. If no timer is specified, the value is set to 'NULL'. We then know that it is a simple event.



DONT FORGET TO SPECIFY THE MYSQL CREDENTIALS AND THE PATH TO THE FILE RECORDING THE FAILED SQL CALL!
Row.connect()
FAILEDSQL


Improvements:
Add more softwares 
If you can have a database by software, it can be useful to have a table by tool instead.
"""

import io
import os
import sys
import time
import uuid
import logging
import datetime
import threading
import MySQLdb
logger = logging.getLogger(__name__)


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


class Datetimer(object):
    def __init__(self):
        self.date = datetime.datetime.now()

    def getElapsedTime(self):
        self.elapsed = datetime.datetime.now() - self.date
        self.elapsed = self.elapsed.total_seconds()
        return self.elapsed


class Stats(object):
    def __init__(self, tool, author, version):
        self.params = {}
        self.params['user'] = self.getUser()
        self.params['author'] = author
        self.params['version'] = version
        self.params['tool'] = tool
        self.params['software'] = self.getSoftware()
        self.params['project'] = 'project code'
        self.params['host'] = 'computer name'
        self.isUserValid()

    def getSoftware(self):
        '''Determine the software name and version.'''
        try:
            import maya.cmds
            self.params['table'] = 'Maya'
            return maya.cmds.about(installedVersion=True)
        except ImportError:
            pass

        try:
            import hou
            self.params['table'] = 'Houdini'
            return hou.applicationVersionString()
        except ImportError:
            pass

        try:
            import mari.app
            self.params['table'] = 'Mari'
            return mari.app.version().string()
        except ImportError:
            pass

        try:
            import nuke
            self.params['table'] = 'Nuke'
            return nuke.NUKE_VERSION_STRING
        except ImportError:
            pass

        try:
            import bpy.app
            self.params['table'] = 'Blender'
            return bpy.app.version_string
        except ImportError:
            pass

        self.params['table'] = 'Unknown'
        return ''

    def getUser(self):
        '''Get the user name'''
        try:
            import pwd
            return pwd.getpwuid(os.getuid()).pw_name
        except ImportError:
            import getpass
            return getpass.getuser()
        return 'unknown'

    def isUserValid(self):
        '''Do not register some users.'''
        special_users = ['captain3d'. 'regnareb']
        if self.params['user'] in special_users:
            self.params['table'] = 'developers'

    def emit(self, status, timer=False):
        return Row(status=status, timer=timer, **self.params)





class Row(object):
    FAILEDSQL = r'the/path/to/the/file/you/want.txt'
    ORDER = ['project', 'software', 'tool', 'author', 'version', 'user', 'host', 'status']
    LIMITS = {'project': 16, 'software': 64, 'tool': 64, 'author': 16, 'version': 16, 'user': 16, 'host': 16, 'status': 64, 'timer': [14, 5]}

    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        self.lock = threading.Lock()
        self.datetimer = Datetimer()
        self.datetimer.elapsed = 0 if kwargs['timer'] else 'NULL'
        self.start()

    def execute(self, cursor, sqlList):
        for sql in sqlLists:
            cursor.execute(sql)
        if not hasattr(self, 'ident'):
            self.ident = cursor.lastrowid

    def connect(self, sql):
        delay = 1
        backoff = 2
        tries = range(2)
        tries.reverse()
        for tries_remaining in tries:
            timeout = 2
            logger.debug('Timeout: {}\Tries remaining: {}\nSQL: {}\n'.format(timeout, tries_remaining, sql))
            try:
                db = MySQLdb.connect(host="localhost", user="user", passwd="password", db="database", connect_timeout=timeout)
                try:
                    with db as cursor:
                        cursor.execute(sql)
                        if not hasattr(self, 'ident'):
                            self.ident = cursor.lastrowid
                except MySQLdb.ProgrammingError, e:
                    if e[0] == 1146: 
                        # The table does not exists, create it
                        cursor.execute(self.createTable())
                        cursor.execute(sql)
                        if not hasattr(self, 'ident'):
                            self.ident = cursor.lastrowid
                    else:
                        raise
                finally:
                    db.close()
            except Exception as e:
                if tries_remaining > 0:
                    time.sleep(delay)
                    delay = delay * backoff
                else:
                    self.failed(sql)
                    # raise
            else:
                break
    @threaded
    def stop(self, elapsed=None):
        with self.lock:
            if not elapsed:
                elapsed = self.datetimer.getElapsedTime()
            sql = """ UPDATE %s SET timer=%s WHERE id=%s;""" % (self.table, elapsed, self.ident)
            self.connect(sql)

    @threaded
    def start(self):
        with self.lock:
            # truncate the data according to their data types in the database
            SQL_STRING = [getattr(self, i).encode('ascii','ignore')[:self.LIMITS[i]] for i in self.ORDER] + [str(self.datetimer.date), self.datetimer.elapsed]
            sql = """ INSERT INTO %s (project, software, tool, author, version, user, host, status, dateTime, timer) VALUES (%s);""" % (self.table, ', '.join(repr(i) if i != 'NULL' else i for i in SQL_STRING))
            self.connect(sql)

    def failed(self, sql):
        if not hasattr(self, 'ident'):
            self.ident = uuid.uuid1()
            logger.debug(self.ident)
        with io.open(self.FAILEDSQL, 'a') as myfile:
            sql = '{}\n{}\n'.format(self.ident, sql)
            myfile.write(sql.decode('utf-8'))

    def createTable(self):
        sql = """CREATE TABLE IF NOT EXISTS {0} (
        id INT NOT NULL AUTO_INCREMENT,
        project VARCHAR({project}) NOT NULL,
        software VARCHAR({software}) NOT NULL,
        tool VARCHAR({tool}) NOT NULL,
        author VARCHAR({author}) NOT NULL,
        version VARCHAR({version}) NOT NULL,
        user VARCHAR({user}) NOT NULL,
        host VARCHAR({host}) NOT NULL,
        status VARCHAR({status}) NOT NULL,
        datetime DATETIME NOT NULL,
        timer FLOAT({timer[0]}, {timer[1]}),
        PRIMARY KEY(id)
        );""".format(self.table, **self.LIMITS)
        return sql
