import time

import cv2
from picamera.array import PiRGBArray
from picamera import PiCamera

from htpa import *

DEBUG = True

TH_SCALE = 1.1
TH_DH = -25
TH_DW = 43

PERIOD_UPDATE_COMPENSATION = 10
RESOLUTION = (640, 480)
OUT_RGB = '../../website/static/rgb.jpg'
OUT_THERMO = '../../website/static/thermo.jpg'
OUT_MERGE = '../../website/static/merge.jpg'
TMAX = 45
TMIN = 15


camera = PiCamera()
camera.resolution = RESOLUTION
camera.framerate = 2
camera.rotation = 180
raw_capture = PiRGBArray(camera, size=(640, 480))

dev_htpa = HTPA(0x1A)

# camera warm-up
time.sleep(1)


def temperatures_to_image(temperatures):
    temperatures = np.clip(temperatures, TMIN, TMAX)
    temperatures = (temperatures - TMIN)/(TMAX - TMIN)
    temperatures *= 255
    # should be changed according to merging considerations
    temperatures = cv2.resize(temperatures, None, fx=18.72, fy=18.72)
    temperatures[0,0] = 255 # so that colors are fixed
    temperatures[0,1] = 0
    temperatures = temperatures.astype(np.uint8)
    img = cv2.applyColorMap(temperatures, cv2.COLORMAP_JET)
    img = cv2.flip(img, 0)
    return img


def print_debug(s):
    if DEBUG:
        print(s)


def save_decay_info(temperatures, f, ta, idx=None):
    tavg = np.mean(temperatures)
    tmax = np.max(temperatures)
    tmin = np.min(temperatures)
    tstd = np.std(temperatures)

    f.write("tmax {} tmin {} tavg {} tstd {} ta {}\n".format(
        tmax, tmin, tavg, tstd, ta))


    if idx != None:
        print("idx {} tmax {} tmin {} tavg {} tstd {} ta {}".format(
              idx, tmax, tmin, tavg, tstd, ta))

        np.savetxt("../../thermo-info/frames/temperatures_{}.txt".format(idx), temperatures)


def capture_loop():
    try:
        with open('readings.txt', 'w') as f:
            for i, frame in enumerate(camera.capture_continuous(raw_capture, format="bgr", use_video_port=True), 0):
                rgb_img = frame.array

                if i % PERIOD_UPDATE_COMPENSATION == 0:
                    dev_htpa.update_compensation_parameters()

                temperatures, t_amb = dev_htpa.capture_temperatures()
                thermo_img = temperatures_to_image(temperatures)

                cv2.imwrite(OUT_RGB, rgb_img)
                cv2.imwrite(OUT_THERMO, thermo_img)
                save_decay_info(temperatures, f, t_amb, idx=i)

                raw_capture.truncate(0)
                time.sleep(1)

    except KeyboardInterrupt:
        print("Exiting loop.")
        return


def close_all():
    camera.close()
    dev_htpa.close()


if __name__ == "__main__":
    
    capture_loop()

    close_all()