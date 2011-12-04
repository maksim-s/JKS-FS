import os
##    File metadata:
##    * st_mode - protection bits,
##    * st_ino - inode number,
##    * st_dev - device,
##    * st_nlink - number of hard links,
##    * st_uid - user id of owner,
##    * st_gid - group id of owner,
##    * st_size - size of file, in bytes,
##    * st_atime - time of most recent access,
##    * st_mtime - time of most recent content modification,
##    * st_ctime - platform dependent; time of most recent metadata change on Unix, or the time of creation on Windows)

##    on linux this might also be available:
##    * st_blocks - number of blocks allocated for file
##    * st_blksize - filesystem blocksize
##    * st_rdev - type of device if an inode device
##    * st_flags - user defined flags for file

class File():

  def getFullPath(self):
    if self.parent is None:
      return self.name
    return self.parent.getFullPath() + '/' + self.name

  def __init__(self, name, parent, stat):
    self.name = name
    self.parent = parent
    self.stat = stat

class Directory(File):

  def __init__(self, name, parent, stat):
    self.name = name
    self.parent = parent
    self.stat = stat
    self.children = []
    
def copyFile(fo, filepath, rootDirLen):
  fo.write("HEADER\n")
  fo.write("ItemType:File\n")
  fo.write(filepath[rootDirLen:] + "\n")
  (mode,ino,dev,nlink,uid,gid,size,atime,mtime,ctime) = os.stat(filepath)
  fo.write("Stats:\n")
  stats = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n"%(mode,ino,dev,nlink,uid,gid,size,atime,mtime,ctime)
  fo.write(stats)
  size = os.path.getsize(filepath)
  fo.write("Size:\n")
  fo.write(str(size) + "\n")
  fo.write("Content:\n")
  fd2 = os.open(filepath, os.O_RDWR)
  str2 = os.read(fd2, size)
  fo.write(str2)
  fo.write("\n")
  return True

def copyDirectory(fo, dirpath, rootDirLen):
  fo.write("HEADER\n")
  fo.write("ItemType:Directory\n")
  fo.write(dirpath[rootDirLen:] + "\n")
  (mode,ino,dev,nlink,uid,gid,size,atime,mtime,ctime) = os.stat(dirpath)
  
  fo.write("Stats:\n")
#  fo.write("(mode,ino,dev,nlink,uid,gid,size,atime,mtime,ctime)\n")
  stats = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n"%(mode,ino,dev,nlink,uid,gid,size,atime,mtime,ctime)
  fo.write( stats)

##patching file
def patchDirectory(rootDir):
  rootDirLen = len(rootDir)
  patch = '/afs/athena.mit.edu/user/k/a/kaynar/Desktop/6.858/root.txt'
  if os.path.exists(patch):
    os.remove(patch)
  fd = os.open( patch, os.O_RDWR|os.O_CREAT )
  fo = os.fdopen(fd, 'w+')
  dirsToVisit = [rootDir]
  while len(dirsToVisit) > 0:
    curDir = dirsToVisit.pop(0)    
    copyDirectory(fo, curDir, rootDirLen)
    dirList = os.listdir(curDir)
    for item in dirList:
      itemFullPath = os.path.join(curDir, item)
      if os.path.isdir(itemFullPath):
        dirsToVisit.append(itemFullPath)
      else:
        copyFile(fo, itemFullPath, rootDirLen)
  fo.close()
  return True

##parser and directory creator
def dispatchDirectory(newDirPath, seekLocation):
  print "new dir path %s" % newDirPath
  patch = '/afs/athena.mit.edu/user/k/a/kaynar/Desktop/6.858/root.txt'
  f = open(patch, 'r')
  fileSize = os.path.getsize(patch)
  f.seek(seekLocation)
  isDir = False
  nextLine = ''
  curPath = ''
  size = 0
  curFile = None
  (mode,ino,dev,nlink,uid,gid,size,atime,mtime,ctime) = (0,0,0,0,0,0,0,0,0,0)
  while f.tell() != fileSize:
    line = f.readline()
    #print f.tell()
    line = line.strip()
    print "line: %s"%line
    if nextLine == "File":
      print 'file'
      curPath = newDirPath + line
      print "new cur path %s" % curPath
      #curFile = open(curPath, 'w')
    elif nextLine == "Directory":
      print 'dir'
      curPath = newDirPath+line
      print "new cur path %s" % curPath
      print line
      isDir = True
      
      #os.mkdir(curPath)
    elif nextLine == "Stats":
      l = line
      arrStats = l.split(',')
      print arrStats
      (mode,ino,dev,nlink,uid,gid,size,atime,mtime,ctime) = arrStats
      if isDir:
        print 'creating new dir'
        os.mkdir(curPath, int(mode))
        os.utime(curPath, (int(atime), int(mtime)))
        isDir = False
    elif nextLine == "Size":
      size = line
      size = int(size)

    nextLine = ''
    if line == "HEADER":
      print "header"
    elif line == "ItemType:File":
      nextLine = "File"
    elif line == "ItemType:Directory":
      print "going to directory"
      nextLine = "Directory"
    elif line == "Stats:":
      print "going to stats"
      nextLine = "Stats"
    elif line == "Size:":
      nextLine = "Size"
    elif line == "Content:":
      nextLine = "Content"
      seekLocation = f.tell()
      break
    print nextLine

  if nextLine == 'Content':
    print "creating a file %s" % curPath
    fd1 = os.open( curPath, os.O_RDWR|os.O_CREAT, int(mode))
    fo1 = os.fdopen(fd1, 'w+')
    fd2 = os.open(patch, os.O_RDWR)
    os.lseek(fd2, seekLocation, 0)
    print seekLocation
    print "size: %s" %size
    text = os.read(fd2, size)
    print text
    fo1.write(text)
    fo1.close()
    os.utime(curPath, (int(atime), int(mtime)))
    seekLocation = f.tell() + size
    print "going one level down %s" % newDirPath
    return dispatchDirectory(newDirPath, seekLocation)
      ##new file/directory
  return True

## deleting fiiles + shredding them
def deleteFiles(dirList, dirPath):
    for fileName in dirList:
        print "Deleting " + fileName
        result = 'boob'
        shreded = False
        while result == 'boob':
          #print "bla"
          if not shreded:
            result = os.system('shred ' + dirPath + "/" +fileName)
            shreded = True
        #os.remove(dirPath + "/" + fileName)

def removeDirectory(dirEntry):
    retVal = []
    print "Deleting files in " + dirEntry[0]
    deleteFiles(dirEntry[2], dirEntry[0])
    retVal.insert(0, dirEntry[0])
    return retVal
  
def clean(path):
    emptyDirs = []
    tree = os.walk(path)
    for directory in tree:
        emptyDir = removeDirectory(directory)
        emptyDirs = emptyDir + emptyDirs
    os.system('rm -rf ' + path)
  
