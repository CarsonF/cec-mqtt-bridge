#!/usr/bin/env bash
set -ex

sudo hostnamectl set-hostname --static pi-bedroom-tv.local

PYTHON_VERSION=3.7.3
sudo apt-get update
sudo apt-get install libffi-dev build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev
wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz
tar xzvf Python-${PYTHON_VERSION}.tgz
cd Python-${PYTHON_VERSION}/
./configure
make -j4
sudo make install
sudo ln -s python /usr/local/bin/python3
# Needed bc cec installs to dist-packages, but python doesn't seem to know about that
sudo ln -s site-packages /usr/local/lib/python${PYTHON_VERSION:0:3}/dist-packages

cd
P8_PLATFORM_VERSION=2.1.0.1
PYTHON_LIBDIR=$(python -c 'from distutils import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')
PYTHON_LDLIBRARY=$(python -c 'from distutils import sysconfig; print(sysconfig.get_config_var("LDLIBRARY"))')
PYTHON_LIBRARY="${PYTHON_LIBDIR}/${PYTHON_LDLIBRARY}"
PYTHON_INCLUDE_DIR=$(python -c 'from distutils import sysconfig; print(sysconfig.get_python_inc())')
wget https://github.com/Pulse-Eight/platform/archive/p8-platform-${P8_PLATFORM_VERSION}.tar.gz
tar xvzf p8-platform-${P8_PLATFORM_VERSION}.tar.gz
rm p8-platform-*.tar.gz
mv platform* p8-platform
mkdir p8-platform/build
cd p8-platform/build
# Changed install prefix to match python 3.7 install
cmake -DCMAKE_INSTALL_PREFIX:PATH=/usr/local \
  ..
make -j4
sudo make install

cd
LIBCEC_VERSION=4.0.4
wget https://github.com/Pulse-Eight/libcec/archive/libcec-${LIBCEC_VERSION}.tar.gz
tar xzvf libcec-${LIBCEC_VERSION}.tar.gz
rm libcec-*.tar.gz
mv libcec* libcec
mkdir libcec/build
cd libcec/build
# Changed install prefix to match python 3.7 install
cmake -DCMAKE_INSTALL_PREFIX:PATH=/usr/local \
   -DRPI_INCLUDE_DIR=/opt/vc/include \
   -DRPI_LIB_DIR=/opt/vc/lib \
   -DPYTHON_LIBRARY="${PYTHON_LIBRARY}" \
   -DPYTHON_INCLUDE_DIR="${PYTHON_INCLUDE_DIR}" \
   -DPYTHON_LIB_INSTALL_PATH="" \
   ..
make -j4
sudo make install

cd
rm -rf p8-platform libcec
