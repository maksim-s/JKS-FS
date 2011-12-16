#!/usr/bin/env python

import os, sys
from errno import *
from stat import *
from directory import *
import getpass
import fcntl
from steganography import Encoder, Decoder, ImageLinker
import fuse
from fuse import Fuse


if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."

fuse.fuse_python_api = (0, 2)

# We use a custom file class
fuse.feature_assert('stateful_files', 'has_init')


def flag2mode(flags):
    md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)

    return m

def createTmpFolder(path):
    folderName = os.path.join(path, 'jks-fs')
    while(os.path.exists(folderName)):
      folderName += '1'
    os.mkdir(folderName)
    return os.path.abspath(os.path.curdir) +'/' + folderName

def createEmptyName(path):
    folderName = os.path.join(path, 'jks-fs')
    while(os.path.exists(folderName)):
      folderName += '1'
    return os.path.join(os.path.abspath(os.path.curdir), folderName)

def createTmpFile(abspath, folderName):
    filename = abspath+'/' + folderName+'/jks-fs'
    while(os.path.exists(folderName+'.txt')):
        filename += '1'
    filename +=  '.txt'
    f = open(filename , 'w')
    f.close()
    return filename


def removeFilePermanently(fileName):
  ##shred fileName
  result = 'inLoop'
  shreded = False
  while result == 'inLoop':
    #print "bla"
      if not shreded:
          result = os.system('shred ' + fileName)
          shreded = True
  os.remove(fileName)

class Xmp(Fuse):
    def __init__(self, *args, **kw):
        arguments = sys.argv
        mount_type = arguments[1]
        self.image_folder = arguments[2]
        self.abspath = os.path.abspath(os.path.curdir)
        self.password = getpass.getpass()
        self.mount_folder = self.abspath + '/' + arguments[3]
        if mount_type == 'create':
            self.root = createTmpFolder(self.image_folder )    
            imageLinker = ImageLinker(os.path.join(self.abspath, self.image_folder), self.password)
            imageLinker.linkImages()    
        
        if mount_type == 'mount':
            self.root = createEmptyName(self.image_folder)           
            fileName = createTmpFile(self.abspath, self.image_folder)
            decoder = Decoder(fileName, os.path.join(self.abspath, self.image_folder), self.password)
            (successBoolean, message) = decoder.decodePatch()            
            dispatchDirectory(fileName, self.root, 0)
            removeFilePermanently(fileName)
        Fuse.__init__(self, *args, **kw)
        self.file_class = self.XmpFile

    def getattr(self, path):
        return os.lstat("." + path)

    def readlink(self, path):
        return os.readlink("." + path)

    def readdir(self, path, offset):
        for e in os.listdir("." + path):
            yield fuse.Direntry(e)

    def unlink(self, path):
        os.unlink("." + path)

    def rmdir(self, path):
        os.rmdir("." + path)

    def symlink(self, path, path1):
        os.symlink(path, "." + path1)

    def rename(self, path, path1):
        os.rename("." + path, "." + path1)

    def link(self, path, path1):
        os.link("." + path, "." + path1)

    def chmod(self, path, mode):
        os.chmod("." + path, mode)

    def chown(self, path, user, group):
        os.chown("." + path, user, group)

    def truncate(self, path, len):
        f = open("." + path, "a")
        f.truncate(len)
        f.close()

    def mknod(self, path, mode, dev):
        os.mknod("." + path, mode, dev)

    def mkdir(self, path, mode):
        os.mkdir("." + path, mode)

    def utime(self, path, times):
        os.utime("." + path, times)


    def fsdestroy(self, data = None):
        tmpFile = createTmpFile(self.abspath, self.image_folder)
        patchDirectory(self.root, tmpFile)
        encoder = Encoder(tmpFile,self.abspath+ '/' + self.image_folder, self.password)
        encoder.encodePatch()
        removeFilePermanently(tmpFile)
        os.rmdir(self.mount_folder)
        emptyDirs = clean(self.root) ##self.mount_dir

    def access(self, path, mode):
        if not os.access("." + path, mode):
            return -EACCES


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

    def fsinit(self):
        os.chdir(self.root)

    class XmpFile(object):

        def __init__(self, path, flags, *mode):
            self.file = os.fdopen(os.open("." + path, flags, *mode),
                                  flag2mode(flags))
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

        def lock(self, cmd, owner, **kw):
            # The code here is much rather just a demonstration of the locking
            # API than something which actually was seen to be useful.

            # Advisory file locking is pretty messy in Unix, and the Python
            # interface to this doesn't make it better.
            # We can't do fcntl(2)/F_GETLK from Python in a platfrom independent
            # way. The following implementation *might* work under Linux. 
            #
            # if cmd == fcntl.F_GETLK:
            #     import struct
            # 
            #     lockdata = struct.pack('hhQQi', kw['l_type'], os.SEEK_SET,
            #                            kw['l_start'], kw['l_len'], kw['l_pid'])
            #     ld2 = fcntl.fcntl(self.fd, fcntl.F_GETLK, lockdata)
            #     flockfields = ('l_type', 'l_whence', 'l_start', 'l_len', 'l_pid')
            #     uld2 = struct.unpack('hhQQi', ld2)
            #     res = {}
            #     for i in xrange(len(uld2)):
            #          res[flockfields[i]] = uld2[i]
            #  
            #     return fuse.Flock(**res)

            # Convert fcntl-ish lock parameters to Python's weird
            # lockf(3)/flock(2) medley locking API...
            op = { fcntl.F_UNLCK : fcntl.LOCK_UN,
                   fcntl.F_RDLCK : fcntl.LOCK_SH,
                   fcntl.F_WRLCK : fcntl.LOCK_EX }[kw['l_type']]
            if cmd == fcntl.F_GETLK:
                return -EOPNOTSUPP
            elif cmd == fcntl.F_SETLK:
                if op != fcntl.LOCK_UN:
                    op |= fcntl.LOCK_NB
            elif cmd == fcntl.F_SETLKW:
                pass
            else:
                return -EINVAL

            fcntl.lockf(self.fd, op, kw['l_start'], kw['l_len'])



def main():
    
    ##create a new directory
    newDir =os.path.join(os.getcwd(), sys.argv[-1])
    if not os.path.exists(newDir):
      os.mkdir(newDir)


    usage = """
Userspace nullfs-alike: mirror the filesystem tree from some point on.

""" + Fuse.fusage

    server = Xmp(version="%prog " + fuse.__version__,
                 usage=usage)

    server.parser.add_option(mountopt="root", metavar="PATH", default='/',
                             help="mirror filesystem from under PATH [default: %default]")


    server.parse(values=server, errex=1)

    try:
        if server.fuse_args.mount_expected():
            os.chdir(server.root)
    except OSError:
        print >> sys.stderr, "can't enter root of underlying filesystem"
        sys.exit(1)

    server.main()

if __name__ == '__main__':
    main()
