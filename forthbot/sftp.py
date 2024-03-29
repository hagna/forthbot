# ckeygen -t rsa -f id_rsa
# 
# ssh-passwords
# bob:password
# foo:foo

from zope.interface import implements

from twisted.python import components
from twisted.internet.protocol import Protocol
from twisted.python import log
from twisted.cred.portal import Portal
from twisted.cred.checkers import FilePasswordDB
from twisted.conch.ssh.factory import SSHFactory
from twisted.internet import reactor, defer
from twisted.conch.ssh.keys import Key
from twisted.conch.interfaces import IConchUser, ISFTPFile
from twisted.conch.avatar import ConchUser
from twisted.conch.unix import UnixConchUser
from twisted.conch.ssh import filetransfer
from twisted.conch.ssh.session import (
    SSHSession, SSHSessionProcessProtocol, wrapProtocol)


import os, errno

from StringIO import StringIO


class InMemoryFile:

    implements(ISFTPFile)
    
    def __init__(self, data=''):
        self.data = StringIO(data)

    def close(self):
        self.data.seek(0)

    def readChunk(self, offset, length):
        self.data.seek(offset)
        return self.data.read(length)

    def writeChunk(self, offset, data):
        self.data.write(data)
        

    def getAttrs(self):
        current = self.data.tell()
        self.data.seek(0, 2)
        size = self.data.tell()
        self.data.seek(current)
        return {
            'size': size,
            'uid': 22,
            'gid': 23,
            'permissions': 33261,
            'atime': 1322669000,
            'mtime': 1322669000,
        }

    def setAttrs(self, attrs):
        """
        Set the attributes for the file.

        This method returns when the attributes are set or a Deferred that is
        called back when they are.

        @param attrs: a dictionary in the same format as the attrs argument to
        L{openFile}.
        """


class MySFTPAdapter:

    implements(filetransfer.ISFTPServer)


    def __init__(self, avatar):
        self.avatar = avatar
        self.files = {}
    
    
    def gotVersion(self, otherVersion, extData):
        print 'gotVersion', otherVersion, extData
        return {}


    def openFile(self, filename, flags, attrs):
        """
        Called when the clients asks to open a file.

        @param filename: a string representing the file to open.

        @param flags: an integer of the flags to open the file with, ORed together.
        The flags and their values are listed at the bottom of this file.

        @param attrs: a list of attributes to open the file with.  It is a
        dictionary, consisting of 0 or more keys.  The possible keys are::

            size: the size of the file in bytes
            uid: the user ID of the file as an integer
            gid: the group ID of the file as an integer
            permissions: the permissions of the file with as an integer.
            the bit representation of this field is defined by POSIX.
            atime: the access time of the file as seconds since the epoch.
            mtime: the modification time of the file as seconds since the epoch.
            ext_*: extended attributes.  The server is not required to
            understand this, but it may.

        NOTE: there is no way to indicate text or binary files.  it is up
        to the SFTP client to deal with this.

        This method returns an object that meets the ISFTPFile interface.
        Alternatively, it can return a L{Deferred} that will be called back
        with the object.
        """
        print 'openFile', filename
        if (flags & filetransfer.FXF_CREAT) == filetransfer.FXF_CREAT:
            self.files[filename] = InMemoryFile()
        return self.files[filename]


    def removeFile(self, filename):
        """
        Remove the given file.

        This method returns when the remove succeeds, or a Deferred that is
        called back when it succeeds.

        @param filename: the name of the file as a string.
        """
        del self.files[filename]


    def renameFile(self, oldpath, newpath):
        """
        Rename the given file.

        This method returns when the rename succeeds, or a L{Deferred} that is
        called back when it succeeds. If the rename fails, C{renameFile} will
        raise an implementation-dependent exception.

        @param oldpath: the current location of the file.
        @param newpath: the new file name.
        """
        self.files[newpath] = self.files[oldpath]
        del self.files[oldpath]


    def makeDirectory(self, path, attrs):
        """
        Make a directory.

        This method returns when the directory is created, or a Deferred that
        is called back when it is created.

        @param path: the name of the directory to create as a string.
        @param attrs: a dictionary of attributes to create the directory with.
        Its meaning is the same as the attrs in the L{openFile} method.
        """


    def removeDirectory(self, path):
        """
        Remove a directory (non-recursively)

        It is an error to remove a directory that has files or directories in
        it.

        This method returns when the directory is removed, or a Deferred that
        is called back when it is removed.

        @param path: the directory to remove.
        """


    def openDirectory(self, path):
        """
        Open a directory for scanning.

        This method returns an iterable object that has a close() method,
        or a Deferred that is called back with same.

        The close() method is called when the client is finished reading
        from the directory.  At this point, the iterable will no longer
        be used.

        The iterable should return triples of the form (filename,
        longname, attrs) or Deferreds that return the same.  The
        sequence must support __getitem__, but otherwise may be any
        'sequence-like' object.

        filename is the name of the file relative to the directory.
        logname is an expanded format of the filename.  The recommended format
        is:
        -rwxr-xr-x   1 mjos     staff      348911 Mar 25 14:29 t-filexfer
        1234567890 123 12345678 12345678 12345678 123456789012

        The first line is sample output, the second is the length of the field.
        The fields are: permissions, link count, user owner, group owner,
        size in bytes, modification time.

        attrs is a dictionary in the format of the attrs argument to openFile.

        @param path: the directory to open.
        """
        i = []
        path = path.strip('/')
        for name, f in self.files.items():
            if os.path.dirname(name).strip('/') == path:
                i.append(os.path.basename(name), name, {})
        i.close = lambda:None
        return i


    def getAttrs(self, path, followLinks):
        """
        Return the attributes for the given path.

        This method returns a dictionary in the same format as the attrs
        argument to openFile or a Deferred that is called back with same.

        @param path: the path to return attributes for as a string.
        @param followLinks: a boolean.  If it is True, follow symbolic links
        and return attributes for the real path at the base.  If it is False,
        return attributes for the specified path.
        """
        print 'getAttrs', path
        try:
            return self.files[path].getAttrs()
        except:
            raise IOError(errno.ENOENT, "No file")


    def setAttrs(self, path, attrs):
        """
        Set the attributes for the path.

        This method returns when the attributes are set or a Deferred that is
        called back when they are.

        @param path: the path to set attributes for as a string.
        @param attrs: a dictionary in the same format as the attrs argument to
        L{openFile}.
        """
        print 'setAttrs', path, attrs

    def readLink(self, path):
        """
        Find the root of a set of symbolic links.

        This method returns the target of the link, or a Deferred that
        returns the same.

        @param path: the path of the symlink to read.
        """
        print 'readLink', path

    def makeLink(self, linkPath, targetPath):
        """
        Create a symbolic link.

        This method returns when the link is made, or a Deferred that
        returns the same.

        @param linkPath: the pathname of the symlink as a string.
        @param targetPath: the path of the target of the link as a string.
        """
        print 'makeLink', linkPath, targetPath

    def realPath(self, path):
        """
        Convert any path to an absolute path.

        This method returns the absolute path as a string, or a Deferred
        that returns the same.

        @param path: the path to convert as a string.
        """
        if path == '.':
            return '/'
        else:
            return path

    def extendedRequest(self, extendedName, extendedData):
        """
        This is the extension mechanism for SFTP.  The other side can send us
        arbitrary requests.

        If we don't implement the request given by extendedName, raise
        NotImplementedError.

        The return value is a string, or a Deferred that will be called
        back with a string.

        @param extendedName: the name of the request as a string.
        @param extendedData: the data the other side sent with the request,
        as a string.
        """
        print 'extendedRequest', extendedName, extendedDate



class User(ConchUser):


    def __init__(self, username):
        ConchUser.__init__(self)
        self.username = username
    
    
    def __repr__(self):
        return 'User(%r)' % self.username


class DCProtocol(Protocol):


    def connectionMade(self):
        self.transport.close()


class SimpleSession(SSHSession):
    name = 'session'


    def request_pty_req(self, data):
        return True


    def request_shell(self, data):
        protocol = DCProtocol()
        transport = SSHSessionProcessProtocol(self)
        protocol.makeConnection(transport)
        transport.makeConnection(wrapProtocol(protocol))
        self.client = transport
        return True



class SimpleRealm(object):

    def requestAvatar(self, avatarId, mind, *interfaces):
        user = User(avatarId)
        user.channelLookup['session'] = SimpleSession
        user.subsystemLookup.update(
                {'sftp': filetransfer.FileTransferServer})
        return IConchUser, user, lambda:None



components.registerAdapter(MySFTPAdapter, ConchUser, filetransfer.ISFTPServer)




if __name__ == '__main__':
    import sys
    log.startLogging(sys.stdout)
        
    with open('id_rsa') as privateBlobFile:
        privateBlob = privateBlobFile.read()
        privateKey = Key.fromString(data=privateBlob)
    
    with open('id_rsa.pub') as publicBlobFile:
        publicBlob = publicBlobFile.read()
        publicKey = Key.fromString(data=publicBlob)
    
    factory = SSHFactory()
    factory.privateKeys = {'ssh-rsa': privateKey}
    factory.publicKeys = {'ssh-rsa': publicKey}
    factory.portal = Portal(SimpleRealm())
    factory.portal.registerChecker(FilePasswordDB("ssh-passwords"))
    
    reactor.listenTCP(8022, factory)
    reactor.run()
