# Thermografree

## Introduction

This is a fork for [Thermografree](https://github.com/loganwilliams/thermografree/), the first open source, medium resolution, and broadband forward looking infrared (FLIR) camera. It can be used as a thermographic camera, or for scientific imaging applications in the 2-18 um range.

The original project seems to be discontinued, therefore this repository provides an updated driver for the [Datasheet Rev. 11](<docs/datasheets/HTPA32x32dR2L2_1k0.8(Hi)S_Rev11_Datasheet.pdf>). Also, this repository is focused on the software-side, therefore, if you need any help on the construction of the case, or wiring of the devices, please have a look on the [original repository](https://github.com/loganwilliams/thermografree/).

Code is in `src/`, and should work out of the box on a Raspberry Pi with I2C enabled. If you are using an older (2015-2017) verison of the device, you will have to change the HTPA initialization to add an explicit `revision="2017"` in `dualcam.py`. Installation instructions are below.

The application consists of a Python class for interfacing with the module (`htpa.py`) and a GUI (`dualcam.py`). The GUI allows for control of the sensor clock frequency, current, and bias. The default settings are the settings used for the module factory calibration, and seem to produce the best results.

## Installation

### Installing pre-requisites

The Python software has several pre-requisites. To install them on your Raspberry Pi, run the following commands while you have an internet connection.

```
$ sudo apt-get install python-pip \
                       ipython \
                       python-numpy \
                       python-scipy \
                       libopencv-dev \
                       python-opencv \
                       -y
```

```
$ pip install picamera imutils pillow python-periphery --user
```

### Enable I2C

Follow [Adafruit's tutorial](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-4-gpio-setup/configuring-i2c).

### Enabling I2C repeated starts

The I2C hardware on the Raspberry Pi needs to be configured to support "repeated starts." To do this, add the following line to `/etc/modprobe.d/i2c.conf`:

```bash
options i2c-bcm2708 combined=1
```

If you are not using a Raspberry Pi, enabling repeated starts will likely require a different configuration. For more information, see [the blog post I wrote on this topic](http://exclav.es/2016/10/26/talkin-ir/).

## Known issues

-   The sensor calibration programmed into the EEPROM at the factory does not seem to match the noise profile of the images captured from the device.

## LICENSE

MIT License

Copyright (c) 2019 Claudio Busatto

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
