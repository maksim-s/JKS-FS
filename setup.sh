#!/bin/sh -x                                                                           
if id | grep -qv uid=0; then
    echo "Must run setup as root"
    exit 1
fi

easy_install pil
easy_install pycrypto
easy_install fuse-python