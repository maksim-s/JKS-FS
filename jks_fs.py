#!/usr/bin/env python


import os, sys
from errno import *
from stat import *
import fcntl

import fuse
from fuse import Fuse


if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "fuse-py doesn't know of fuse.__version__;it's probably too old."

fuse.fuse_python_api = (0, 2)

# We use a custom file class and fsinit:
fuse.feature_assert('stateful_files', 'has_init')


def flagTomode(flags):
    md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)

    return m


'''Filesystem class'''
class Jks(Fuse):

    # Special filesystem behavior
    def __init__(self, *args, **kw):

        # (TO DO)
        # VALIDATE username, password; Check uid-gid ?
        # If error: Don't mounte FS
        # Else:
        Fuse.__init__(self, *args, **kw)
        self.root = '/tmp/fuse/'
        self.file_class = self.JksFile

    def __del__(self):
        # (TO DO)
        # Recompress and encrypt into Image.
        # Check: Do this here?

# Metadata operations:
    def getattr(self, path):
        return os.lstat("." + path)

    def chmod(self, path, mode):
        os.chmod("." + path, mode)

    def chown(self, path, user, group):
        os.chown("." + path, user, group)

# Directory operations:
    def mkdir(self, path, mode):
        os.mkdir("." + path, mode)

    def readdir(self, path, offset):
        for e in os.listdir("." + path):
            yield fuse.Direntry(e)

    def rmdir(self, path):
        os.rmdir("." + path)

# Basic file operations:
    def unlink(self, path):
        os.unlink("." + path)

    def mknod(self, path, mode, dev):
        os.mknod("." + path, mode, dev)

    def rename(self, path, path1):
        os.rename("." + path, "." + path1)

# Other operations:
    # Hard link; therefore Okay.
    def link(self, path, path1):
        os.link("." + path, "." + path1)

    # (TO DO)
    # Returns the target of a symbolic link;
    # therefore pending discussion with Z
##    def readlink(self, path):
##        return os.readlink("." + path)

    # (TO DO)
    # Returns the target of a symbolic link;
    # therefore pending discussion with Z
##    def symlink(self, path, path1):
##        os.symlink(path, "." + path1)

    def utime(self, path, times):
        os.utime("." + path, times)

    def utimens(self, path, ts_acc, ts_mod):
      os.utime("." + path, (ts_acc.tv_sec, ts_mod.tv_sec))

    def truncate(self, path, len):
        f = open("." + path, "a")
        f.truncate(len)
        f.close()

    def access(self, path, mode):
        if not os.access("." + path, mode):
            return -EACCES

#    This is how we could add stub extended attribute handlers...
#    (We can't have ones which aptly delegate requests to the underlying fs
#    because Python lacks a standard xattr interface.)
#
#    def getxattr(self, path, name, size):
#        val = name.swapcase() + '@' + path
#        if size == 0:
#            # We are asked for size of the value.
#            return len(val)
#        return val
#
#    def listxattr(self, path, size):
#        # We use the "user" namespace to please XFS utils
#        aa = ["user." + a for a in ("foo", "bar")]
#        if size == 0:
#            # We are asked for size of the attr list, ie. joint size of attrs
#            # plus null separators.
#            return len("".join(aa)) + len(aa)
#        return aa

    def statfs(self):
        """
        Should return an object with statvfs attributes (f_bsize, f_frsize...).
        Eg., the return value of os.statvfs() is such a thing (since py 2.2).
        If you are not reusing an existing statvfs object, start with
        fuse.StatVFS(), and define the attributes.

        To provide usable information (ie., you want sensible df(1)
        output, you are suggested to specify the following attributes:

            - f_bsize - preferred size of file blocks, in bytes
            - f_frsize - fundamental size of file blcoks, in bytes
                [if you have no idea, use the same as blocksize]
            - f_blocks - total number of blocks in the filesystem
            - f_bfree - number of free blocks
            - f_files - total number of file inodes
            - f_ffree - nunber of free file inodes
        """

        return os.statvfs(".")

# Meta operations:
    def fsinit(self):
        # (TO DO)
        # Unpatch
        # Decrypt
        # Change root?
        os.chdir(self.root)

''' File class; instantiated for 'open' '''
class JksFile(object):
    def __init__(self, path, flags, *mode):
        self.file = os.fdopen(os.open("." + path, flags, *mode),
                              flagTomode(flags))
        self.fd = self.file.fileno()

    def read(self, length, offset):
        self.file.seek(offset)
        return self.file.read(length)

    def write(self, buf, offset):
        self.file.seek(offset)
        self.file.write(buf)
        return len(buf)

    def release(self, flags):
        self.file.close()

    def _fflush(self):
        if 'w' in self.file.mode or 'a' in self.file.mode:
            self.file.flush()

    def fsync(self, isfsyncfile):
        self._fflush()
        if isfsyncfile and hasattr(os, 'fdatasync'):
            os.fdatasync(self.fd)
        else:
            os.fsync(self.fd)

    def flush(self):
        self._fflush()
        # cf. xmp_flush() in fusexmp_fh.c
        os.close(os.dup(self.fd))

    def fgetattr(self):
        return os.fstat(self.fd)

    def ftruncate(self, len):
        self.file.truncate(len)

def main():

    usage = Fuse.fusage
    server = Xmp(version="%prog " + fuse.__version__,
                 usage=usage)

    server.parser.add_option(mountopt="root",
                             metavar="PATH",
                             default='/tmp/fuse/',
                             help="mirror filesystem from under PATH [default: %default]")
    server.parse(values=server, errex=1)

    #try:
    #    if server.fuse_args.mount_expected():
    #        os.chdir(server.root)
    #except OSError:
    #    print >> sys.stderr, "Can't enter root of underlying filesystem"
    #    sys.exit(1)

    server.main()


if __name__ == '__main__':
    main()
