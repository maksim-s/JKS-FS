import os
import subprocess, sys
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
  os.close(fd2)
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
def patchDirectory(rootDir, patchName):
  rootDirLen = len(rootDir)
  patch = patchName
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
def dispatchDirectory(patchName, newDirPath, seekLocation):
  patch = patchName
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
    line = line.strip()
    if nextLine == "File":
      curPath = newDirPath + line
      #curFile = open(curPath, 'w')
    elif nextLine == "Directory":
      curPath = newDirPath+line
      isDir = True
      
      #os.mkdir(curPath)
    elif nextLine == "Stats":
      l = line
      arrStats = l.split(',')
      (mode,ino,dev,nlink,uid,gid,size,atime,mtime,ctime) = arrStats
      if isDir:
        os.mkdir(curPath, int(mode))
        os.utime(curPath, (int(atime), int(mtime)))
        isDir = False
    elif nextLine == "Size":
      size = line
      size = int(size)

    nextLine = ''
    if line == "ItemType:File":
      nextLine = "File"
    elif line == "ItemType:Directory":
      nextLine = "Directory"
    elif line == "Stats:":
      nextLine = "Stats"
    elif line == "Size:":
      nextLine = "Size"
    elif line == "Content:":
      nextLine = "Content"
      seekLocation = f.tell()
      break

  if nextLine == 'Content':
    fd1 = os.open( curPath, os.O_RDWR|os.O_CREAT, int(mode))
    fo1 = os.fdopen(fd1, 'w+')
    fd2 = os.open(patch, os.O_RDWR)
    os.lseek(fd2, seekLocation, 0)
    text = os.read(fd2, size)
    fo1.write(text)
    fo1.close()
    os.close(fd2)
    os.utime(curPath, (int(atime), int(mtime)))
    seekLocation = f.tell() + size
    f.close()
    return dispatchDirectory(patchName, newDirPath, seekLocation)
      ##new file/directory
  f.close()
  return True

## deleting fiiles + shredding them
def deleteFiles(dirList, dirPath):
    for fileName in dirList:
        result = 'inLoop'
        shreded = False
        while result == 'inLoop':
            if not shreded:
                result = os.system('shred '+ dirPath + "/" + fileName)
                shreded = True
        os.remove(dirPath + "/" + fileName)
    
def removeDirectory(dirEntry):
    retVal = []
    deleteFiles(dirEntry[2], dirEntry[0])
    retVal.insert(0, dirEntry[0])
    return retVal
  
def clean(path):
    emptyDirs = []
    tree = os.walk(path)
    for directory in tree:
        emptyDir = removeDirectory(directory)
        emptyDirs = emptyDir + emptyDirs 

    for emptyDir in emptyDirs:
        os.rmdir(emptyDir)
    return True


