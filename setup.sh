#!/usr/bin/env bash
set -ex

# sudo hostnamectl set-hostname --static pi-bedroom-tv.local

sudo apt-get update
sudo apt-get install git cmake build-essential python3-pkgconfig swig3.0 libudev-dev

cd
P8_PLATFORM_VERSION=2.1.0.1
wget https://github.com/Pulse-Eight/platform/archive/p8-platform-${P8_PLATFORM_VERSION}.tar.gz
tar xvzf p8-platform-${P8_PLATFORM_VERSION}.tar.gz
rm p8-platform-*.tar.gz
mv platform* p8-platform
mkdir p8-platform/build
cd p8-platform/build
cmake ..
make -j4
sudo make install
sudo ldconfig

cd
LIBCEC_VERSION=4.0.4
wget https://github.com/Pulse-Eight/libcec/archive/libcec-${LIBCEC_VERSION}.tar.gz
tar xzvf libcec-${LIBCEC_VERSION}.tar.gz
rm libcec-*.tar.gz
mv libcec* libcec
mkdir libcec/build
cd libcec/build
cmake \
   -DRPI_INCLUDE_DIR=/opt/vc/include \
   -DRPI_LIB_DIR=/opt/vc/lib \
   ..
make -j4
sudo make install
sudo ldconfig

cd
rm -rf p8-platform libcec
