import cv2
import numpy as np

from htpa import *


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

        np.savetxt("./frames/temperatures_{}.txt".format(idx), temperatures)


def test_temperature_decay(max_iters=60, dt=1):
    print("Begin test_temperature_decay")

    dev = HTPA(0x1A)
    try:
        with open('readings.txt', 'w') as f:
            for i in range(max_iters):
                if i % 10 == 0 and i > 0:
                    dev.update_compensation_parameters()

                temperatures, ta = dev.capture_temperatures()
                save_decay_info(temperatures, f, ta, idx=i)

                time.sleep(dt)
             
    except KeyboardInterrupt:
        dev.close()
        print("Exiting loop.")


def test_temperature_capture():
    dev = HTPA(0x1A)
    
    temperatures, ta = dev.capture_temperatures()
    
    print("Ambient temperature: {}".format(ta))
    print("Temperatures: ")
    print(temperatures)

    dev.close()


def save_heatmap(temperatures, pathout, t_min=0, t_max=40):
    temperatures = np.clip(temperatures, t_min, t_max)
    temperatures = (temperatures - t_min)/(t_max - t_min)
    temperatures *= 255
    temperatures = cv2.resize(temperatures, None, fx=12, fy=12)
    temperatures[0,0] = 255
    temperatures[0,1] = 0
    temperatures = temperatures.astype(np.uint8)
    temperatures = cv2.applyColorMap(temperatures, cv2.COLORMAP_JET)
    cv2.imwrite(pathout, temperatures)


def heatmap_capture_loop(pathout):
    dev = HTPA(0x1A)
    max_iters = 200
    try:
        for i in range(max_iters):
            if i % 20 == 0 and i > 0:
                dev.update_compensation_parameters()

            temperatures, ta = dev.capture_temperatures()
            save_heatmap(temperatures, pathout)

            print("{} average: {} std: {} tamb: {}".format(
                i, np.mean(temperatures), np.std(temperatures), ta))

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Exiting loop")
        dev.close()


if __name__ == "__main__":
    path = "../website/static/thermo.jpg"
    test_temperature_decay(max_iters=8200, dt=0.5)
    