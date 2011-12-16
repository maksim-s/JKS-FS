import sys, os, struct, random, gzip, StringIO, hashlib
import Image
from Crypto.Cipher import Blowfish as bf 

# assuming here that file names cannot be changed
# last 11 pixels of an image are for the pointer to the next image
# last 11 pixels: im[-11:][len(im.size[1])] -> e.g. (x,y) = (502-512, 512)
# get the names of the images and 8 byte hash values of the names
def getImageFiles(path):
    files = os.listdir(path)
    imgs = {}
    for f in files:
        if f[-4:] == '.png':
            h = hashlib.sha256(path + '/' + f).hexdigest()
            imgs[int(h[:8], 16)] = path + '/' + f
    return imgs

# compress data with gzip and return output as string
def compress(data):
    buf = StringIO.StringIO()
    gz = gzip.GzipFile(mode='w', fileobj = buf)
    gz.write(data)
    gz.close()
    output = buf.getvalue()
    buf.close()
    return output

# decompress data with gzip and return output as string
def decompress(data):
    buf = StringIO.StringIO(data)
    gz = gzip.GzipFile(mode = "r", fileobj = buf)
    output = gz.read()
    gz.close()
    buf.close()
    return output

# encrypt data using a key for Blowfish
def encrypt(key, iv, data):
    padding = "\x00" * (8 - len(data) % 8) if len(data) != 8 else ""
    key = hashlib.sha256(key).digest()[:7]
    return bf.new(key, bf.MODE_CBC, iv).encrypt(data + padding)

# decrypt data with a key using Blowfish
def decrypt(key, iv, data):
    key = hashlib.sha256(key).digest()[:7]
    return bf.new(key, bf.MODE_CBC, iv).decrypt(data)

class ImageLinker:
    def __init__(self, imgs_path, psswd):
        self.imgs = getImageFiles(imgs_path)
        self.imgs_path = imgs_path
        self.psswd = int(hashlib.sha256(psswd).hexdigest()[:8], 16)
        head = [self.imgs_path + '/' + f
                for f in os.listdir(self.imgs_path)
                if f[-4:] == '.png'][0]
        im = Image.open(head).convert('RGB')
        self.head_img = (head, im)

    # encodes the password in the first 11 pixels of the head image
    # this function assumes that the image is at least 11 pixels wide
    def encodePsswd(self):
        psswd = self.psswd
        pix = self.head_img[1].load()
        w = 10
        h = 0
        pix_2 = pix[w, h][2]
        pix_1 = (pix[w, h][1] & (~1)) | (psswd & 1)
        psswd = psswd >> 1
        pix_0 = (pix[w, h][0] & (~1)) | (psswd & 1)
        psswd = psswd >> 1
        pix[10, 0] = (pix_0, pix_1, pix_2)
        for x in range(1, 11):
            pix_2 = (pix[w - x, h][2] & (~1)) | (psswd & 1)
            psswd = psswd >> 1
            pix_1 = (pix[w - x, h][1] & (~1)) | (psswd & 1)
            psswd = psswd >> 1
            pix_0 = (pix[w - x, h][0] & (~1)) | (psswd & 1)
            psswd = psswd >> 1
            pix[w - x, h] = (pix_0, pix_1, pix_2)
        self.head_img[1].save(self.head_img[0], 'PNG')


    # takes a dictionary of imgs and links them all together
    # by encoding the last 11 pixels of each image to point
    # to the next image. Returns the first/head image.
    def linkImages(self):
        self.encodePsswd()
        image_files = [self.imgs_path + '/' + f
                       for f in os.listdir(self.imgs_path) 
                       if f[-4:] == '.png']
        for i in range(len(image_files)):
            if i == len(image_files) - 1:
                ptr = 0
            else:
                f = image_files[i+1]
                h = hashlib.sha256(f).hexdigest()[:8]
                ptr = int(h, 16)
            self.encodePtr(image_files[i], ptr)
        return image_files[0]

    # encodes the pointer to the next image in the last 11 pixels of img.
    def encodePtr(self, img, ptr):
        im = Image.open(img).convert('RGB')
        pix = im.load()
        h = im.size[1] - 1
        w = im.size[0] - 1
        pix_2 = pix[w, h][2]
        pix_1 = (pix[w, h][1] & (~1)) | (ptr & 1)
        ptr = ptr >> 1
        pix_0 = (pix[w, h][0] & (~1)) | (ptr & 1)
        ptr = ptr >> 1
        pix[w, h] = (pix_0, pix_1, pix_2)
        for x in range(1, 11):
            pix_2 = (pix[w - x, h][2] & (~1)) | (ptr & 1)
            ptr = ptr >> 1
            pix_1 = (pix[w - x, h][1] & (~1)) | (ptr & 1)
            ptr = ptr >> 1
            pix_0 = (pix[w - x, h][0] & (~1)) | (ptr & 1)
            ptr = ptr >> 1
            pix[w - x, h] = (pix_0, pix_1, pix_2)
        im.save(img, 'PNG')

class Encoder(object):
    def __init__(self, patch_path, imgs_path, psswd):
        self.patch_path = patch_path
        self.imgs_path = imgs_path
        self.key = psswd
        self.psswd = int(hashlib.sha256(psswd).hexdigest()[:8], 16)
        self.imgs = getImageFiles(imgs_path)
        head = [self.imgs_path + '/' + f
                for f in os.listdir(self.imgs_path)
                if f[-4:] == '.png'][0]
        im = Image.open(head).convert('RGB')
        self.head_img = (head, im)

    # checks if the password decoded from the head image matches the given password
    def checkPsswd(self):
        if self.psswd == self.getPsswd():
            return True
        else:
            return False

    # decodes the password from the first 11 pixels of the head image
    def getPsswd(self):
        pix = self.head_img[1].load()
        w = 10
        h = 0
        vector = 0
        for x in reversed(range(1, 11)):
            vector = (vector | (pix[w-x, h][0] & 1)) << 1
            vector = (vector | (pix[w-x, h][1] & 1)) << 1
            vector = (vector | (pix[w-x, h][2] & 1)) << 1
        vector = (vector | (pix[w, h][0] & 1)) << 1
        vector = (vector | (pix[w, h][1] & 1))
        return vector

    # read the last 11 pixels of the image to get the hash and then 
    # lookup the name of the next image. Note: first 32 bits only, 
    # the last bit is not used.
    def getNextImage(self, image_name):
        im = image_name[1]
        pix = im.load()
        h = im.size[1] - 1
        w = im.size[0] - 1
        vector = 0
        for x in reversed(range(1, 11)):
            vector = (vector | (pix[w-x, h][0] & 1)) << 1
            vector = (vector | (pix[w-x, h][1] & 1)) << 1
            vector = (vector | (pix[w-x, h][2] & 1)) << 1
        vector = (vector | (pix[w, h][0] & 1)) << 1
        vector = (vector | (pix[w, h][1] & 1))
        if vector == 0:
            return 'None', 0
        else:
            im = Image.open(self.imgs[vector]).convert('RGB')
            return self.imgs[vector], im

    # given current image name, (x, y) cooridnates of the pixel
    # and the R/G/B ch returns the next pixel, channel 
    # and image name to encode the data
    def nextBit(self, x, y, ch, image):
        im = image[1]
        h = im.size[1] - 1
        w = im.size[0] - 1
        if image[0] == self.head_img[0] and x <= 10 and y == 0:
            if ch < 2:
                return (11, y, ch + 1, image)
            else:
                return (11, y, 0, image)
        if y == h and x >= w - 11:
            next_image = self.getNextImage(image)
            return (0, 0, 0, next_image)
        elif x == w:
            if ch < 2:
                return (x, y, ch + 1, image)
            else:
                return (0, y + 1, 0, image)
        else:
            if ch < 2:
                return (x, y, ch + 1, image)
            else:
                return (x + 1, y, 0, image)
        

    # given the first image of the linked list of images, encodes the
    # data string into the images in the linked list
    def encodeData(self, head_img, data):
        im = head_img[1]
        pix = im.load()
        image_name = head_img
        new_image_name = head_img
        x, y, ch = 0, 0, 0
        length = struct.pack('i', len(data))
        for i in range(len(data) + 4):
            b = ord(length[i] if i < 4 else data[i - 4])
            for j in range(8):
                if new_image_name[0] == head_img[0]:
                    x, y, ch, new_image_name = self.nextBit(x, y, ch, new_image_name)
                if new_image_name[0] != image_name[0]:
                    im.save(image_name[0], 'PNG')
                    im = new_image_name[1]
                    pix = im.load()
                    image_name = new_image_name
                p = list(pix[x, y])
                p[ch] = (p[ch] &~ 1) | ((b & (1<<(7 - j))) >> (7 - j))
                pix[x, y] = tuple(p)
                x, y, ch, new_image_name = self.nextBit(x, y, ch, new_image_name)
        im.save(image_name[0], 'PNG')

    def encodePatch(self):
        if self.checkPsswd():
            max_size = 0
            for i in self.imgs:
                im = Image.open(self.imgs[i]).convert('RGB')
                max_size += (im.size[0]*im.size[1]-11)*3
            fin = open(self.patch_path)        
            data = compress(fin.read())
            if max_size < len(data)*8:
                return False, 'Not enough space'
            else:
                length = struct.pack('i', len(data))
                iv = struct.pack("Q", random.getrandbits(64))
                self.encodeData(self.head_img, length + iv + encrypt(self.key, iv, data))
                return True, 'Success'
        else:
            return False, 'Wrong Password'



class Decoder(Encoder):
    def __init__(self, patch_path, imgs_path, psswd):
        super(Decoder, self).__init__(patch_path, imgs_path, psswd)

    # given the first image of the linked list of images, returns the
    # data encoded in the linked list
    def decodeData(self):
        data = ""
        size, length = 4, 0
        x, y, ch, i = 0, 0 , 0, 0
        im = self.head_img[1]
        pix = im.load()
        image_name = self.head_img
        new_image_name = self.head_img
        while i < size:
            byte = 0
            for j in range(8):
                if new_image_name[0] == self.head_img[0]:
                    x, y, ch, new_image_name = self.nextBit(x, y, ch, new_image_name)
                if new_image_name[0] != image_name[0]:
                    im = new_image_name[1]
                    pix = im.load()
                    image_name = new_image_name
                byte |= ((pix[x, y][ch] & 1) << (7 - j))
                x, y, ch, new_image_name = super(Decoder, 
                                                 self).nextBit(x, 
                                                               y, 
                                                               ch, 
                                                               new_image_name)
            if i < 4:
                length |= (byte << (i * 8))
                if i == 3: 
                    size += length
            else:
                data += chr(byte)
            i += 1
        return data

    def decodePatch(self):
        if super(Decoder, self).checkPsswd():
            data = self.decodeData()
            length = struct.unpack('i', data[:4])[0]
            iv, data = data[4:12], data[12:]
            fout = open(self.patch_path, 'w')
            fout.write(decompress(decrypt(self.key, iv, data)[:length]))
            fout.close()
            return True, 'Success'
        else:
            return False, 'Wrong Password'


