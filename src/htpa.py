import time
import struct
import copy

import numpy as np
from periphery import I2C

import interpolate

# from defs.h of Table Number 114
PCSCALEVAL = 1e8


# registers
REG_CONFIG = 0x01
REG_STATUS = 0x02
REG_MBIT = 0x03
REG_BIAS_TOP = 0x04
REG_BIAS_BOT = 0x05
REG_CLK = 0x06
REG_BPA_TOP = 0x07
REG_BPA_BOT = 0x08
REG_PU = 0x09


# calibration settings read previously from EEPROM
CAL_MBIT = 0x2C
CAL_BIAS_TOP = 0x05
CAL_BIAS_BOT = 0x05
CAL_CLK = 0x15
CAL_BPA_TOP = 0x03
CAL_BPA_BOT = 0x03
CAL_PU = 0x88


def generate_command(register, value):
    return [I2C.Message([register, value])]


def send_command(dev_i2c, address, cmd, wait=True):
    dev_i2c.transfer(address, cmd)
    if wait:
        time.sleep(0.005)


class HTPA:
    def __init__(self, address, eeprom_address=0x50, verbose=True):
        self.i2c = I2C("/dev/i2c-1")
        self.address = address
        self.eeprom_address = eeprom_address
        self.verbose = verbose
        
        self.mbit = CAL_MBIT
        self.bias_top = CAL_BIAS_TOP
        self.bias_bot = CAL_BIAS_BOT
        self.clk = CAL_CLK
        self.bpa_top = CAL_BPA_TOP
        self.bpa_bot = CAL_BPA_BOT
        self.pull_up = CAL_PU

        self.wake_up_sensor()
        self.set_calibration_settings()
        
        eeprom = self.get_eeprom()
        self.extract_eeprom_parameters(eeprom)

        self.update_compensation_parameters()

    def wake_up_sensor(self):
        self.write_register(REG_CONFIG, 0x01)

    def close(self):
        self.write_register(REG_CONFIG, 0x00)

    def write_register(self, register, value):
        cmd = generate_command(register, value)
        send_command(self.i2c, self.address, cmd)

    def set_calibration_settings(self):
        self.write_register(REG_MBIT, self.mbit)
        self.write_register(REG_BIAS_TOP, self.bias_top)
        self.write_register(REG_BIAS_BOT, self.bias_bot)
        self.write_register(REG_CLK, self.clk)
        self.write_register(REG_BPA_TOP, self.bpa_top)
        self.write_register(REG_BPA_BOT, self.bpa_bot)
        self.write_register(REG_PU, self.pull_up)

    def ambient_temperature(self, ptats):
        return self.ptat_grad * np.mean(ptats) + self.ptat_offset

    def temperature_compensation(self, im, ptats):
        compensation = self.th_grad * np.mean(ptats) / (2 ** self.grad_scale)
        compensation += self.th_offset

        return im - compensation

    def electrical_offset_compensation(self, im):
        return im - self.electrical_offset

    def sensitivity_compensation(self, im):
        return PCSCALEVAL * im / self.pix_c

    def voltage_compensation(self, im, ptats):
        PTATAvg = np.mean(ptats)

        aux1 = self.VddCompGrad * PTATAvg / (2 ** self.VddScGrad) 
        aux1 = (aux1 + self.VddCompOff) / (2 ** self.VddScOff)

        aux2_1 = self.VddAvg - self.VddTh1
        aux2_2 = (self.VddTh2 - self.VddTh1)/(self.PTATTh2 - self.PTATTh1)
        aux2_3 = PTATAvg - self.PTATTh1
        aux2 = aux2_1 - aux2_2*aux2_3
        compensation = aux1 * aux2

        return im - compensation

    def get_eeprom(self):
        q1 = [I2C.Message([0x00, 0x00]), I2C.Message([0x00]*4000, read=True)]
        q2 = [I2C.Message([0x0f, 0xa0]), I2C.Message([0x00]*4000, read=True)]
        self.i2c.transfer(self.eeprom_address, q1)
        self.i2c.transfer(self.eeprom_address, q2)

        return np.array(q1[1].data + q2[1].data)

    def extract_calibration_settings(self, eeprom):
        mbit = eeprom[0x001A]
        bias = eeprom[0x001B]
        clk = eeprom[0x001C]
        bpa = eeprom[0x001D]
        pu = eeprom[0x001E]

        if self.verbose:
            print("Calibration data from eeprom: ")
            print("MBIT (calib): ", hex(mbit))
            print("BIAS (calib): ", hex(bias))
            print("CLK (calib): ", hex(clk))
            print("BPA (calib): ", hex(bpa))
            print("PU (calib): ", hex(pu))

    def extract_temperature_compensation_data(self, eeprom):
        th_grad = eeprom[0x0740:0x0F40:2] + (eeprom[0x0741:0x0F40:2] << 8)
        th_grad = unsigned_to_signed_array(th_grad)
        th_grad = np.reshape(th_grad, (32, 32))
        th_grad[16:,:] = np.flipud(th_grad[16:,:]) # bottom values are flipped
        self.th_grad = th_grad

        th_offset = eeprom[0x0F40:0x1740:2] + (eeprom[0x0F41:0x1740:2] << 8)
        th_offset = unsigned_to_signed_array(th_offset)
        th_offset = np.reshape(th_offset, (32, 32))
        th_offset[16:,:] = np.flipud(th_offset[16:,:]) # bottom values are flipped
        self.th_offset = th_offset

        self.grad_scale = eeprom[0x0008]
        self.ptat_grad = self.eeprom_value_to_float(eeprom[0x0034:0x0038])
        self.ptat_offset = self.eeprom_value_to_float(eeprom[0x0038:0x003c])

    def extract_sensitivity_compensation_data(self, eeprom):
        pmin = self.eeprom_value_to_float(eeprom[0x0000:0x0004])
        pmax = self.eeprom_value_to_float(eeprom[0x0004:0x0008])
        epsilon = float(eeprom[0x000D])
        global_gain = eeprom[0x0055] + (eeprom[0x0056] << 8)

        P = eeprom[0x1740::2] + (eeprom[0x1741::2] << 8)
        P = np.reshape(P, (32, 32))
        P[16:, :] = np.flipud(P[16:,:])

        self.pix_c = (P * (pmax - pmin) / 65535. + pmin) * (epsilon / 100) 
        self.pix_c *= float(global_gain) / 10000

    def extract_voltage_compensation_data(self, eeprom):
        self.PTATTh1 = eeprom[0x003C] + (eeprom[0x003D] << 8)
        self.PTATTh2 = eeprom[0x003E] + (eeprom[0x003F] << 8)
        self.VddTh1 = eeprom[0x0026] + (eeprom[0x0027] << 8)
        self.VddTh2 = eeprom[0x0028] + (eeprom[0x0029] << 8)
        self.VddScGrad = eeprom[0x004E]
        self.VddScOff = eeprom[0x004F]

        if self.verbose:
            print("Voltage compensation data: ")
            print("PTATTh1: {}".format(self.PTATTh1))
            print("PTATTh2: {}".format(self.PTATTh2))
            print("VddTh1: {}".format(self.VddTh1))
            print("VddTh2: {}".format(self.VddTh2))
            print("VddScGrad: {}".format(self.VddScGrad))
            print("VddScOff: {}".format(self.VddScOff))

        vdd_comp_grad_ep = eeprom[0x0340:0x0540:2] + (eeprom[0x0341:0x0540:2] << 8)
        vdd_comp_grad_ep = [v - 65536 if v >= 32768 else v for v in vdd_comp_grad_ep] # check this line. seems ok
        vdd_comp_grad_ep = np.reshape(vdd_comp_grad_ep, (8, 32))
        vdd_comp_grad_top_block = vdd_comp_grad_ep[0:4, :]
        vdd_comp_grad_bot_block = np.flipud(vdd_comp_grad_ep[4:, :])
        self.VddCompGrad = np.zeros((32, 32))
        for b in range(0, 4):
            self.VddCompGrad[4*b : 4*(b+1), :] = vdd_comp_grad_top_block
            self.VddCompGrad[16 + 4*b : 16 + 4*(b+1), :] = vdd_comp_grad_bot_block

        vdd_comp_off_ep = eeprom[0x0540:0x0740:2] + (eeprom[0x0541:0x0740:2] << 8)
        vdd_comp_off_ep = [v - 65536 if v >= 32768 else v for v in vdd_comp_off_ep] # check this line. seems ok
        vdd_comp_off_ep = np.reshape(vdd_comp_off_ep, (8, 32))
        vdd_comp_off_top_block = vdd_comp_off_ep[0:4, :]
        vdd_comp_off_bot_block = np.flipud(vdd_comp_off_ep[4:, :])
        self.VddCompOff = np.zeros((32, 32))
        for b in range(0, 4):
            self.VddCompOff[4*b : 4*(b+1), :] = vdd_comp_off_top_block
            self.VddCompOff[16 + 4*b : 16 + 4*(b+1), :] = vdd_comp_off_bot_block

    def extract_eeprom_parameters(self, eeprom):
        self.extract_calibration_settings(eeprom)
        self.extract_temperature_compensation_data(eeprom)
        self.extract_sensitivity_compensation_data(eeprom)
        self.extract_voltage_compensation_data(eeprom)

    def update_compensation_parameters(self):
        if self.verbose:
            print("Updating compensation parameters.")

        (offset, vdds) = self.capture_image(blind=True, vdd=True)
        self.electrical_offset = offset
        self.VddAvg = np.mean(vdds)

    def object_temperature(self, ta, ad):
        return interpolate.get_temperature(ta, ad)

    def im_to_temperatures(self, im, ta):
        temperatures = np.zeros((32,32))
        for row in range(32):
            for col in range(32):
                t = self.object_temperature(ta, im[row, col])/10 - 273
                temperatures[row, col] = t

        return temperatures

    def capture_temperatures(self):
        im, ptats = self.capture_image(blind=False, vdd=False)
        im = self.temperature_compensation(im, ptats)
        im = self.electrical_offset_compensation(im)
        im = self.voltage_compensation(im, ptats)
        im = self.sensitivity_compensation(im)

        ta = self.ambient_temperature(ptats)
        temps = self.im_to_temperatures(im, ta)

        return temps, ta

    def capture_image(self, blind=False, vdd=False):
        pixel_values = np.zeros(1024)
        ptats = np.zeros(8)

        for block in range(4):
            self.expose_block(block, blind=blind, vdd=vdd)

            while not self.block_capture_finished(block, blind, vdd):
                time.sleep(0.005)

            read_block = [I2C.Message([0x0A]), I2C.Message([0x00]*258, read=True)]
            self.i2c.transfer(self.address, read_block)
            top_data = np.array(copy.copy(read_block[1].data))

            read_block = [I2C.Message([0x0B]), I2C.Message([0x00]*258, read=True)]
            self.i2c.transfer(self.address, read_block)
            bottom_data = np.array(copy.copy(read_block[1].data))

            top_data = top_data[1::2] + (top_data[0::2] << 8)
            bottom_data = bottom_data[1::2] + (bottom_data[0::2] << 8)

            pixel_values[(0+block*128):(128+block*128)] = top_data[1:]
            # bottom data is in a weird shape
            pixel_values[(992-block*128):(1024-block*128)] = bottom_data[1:33]
            pixel_values[(960-block*128):(992-block*128)] = bottom_data[33:65]
            pixel_values[(928-block*128):(960-block*128)] = bottom_data[65:97]
            pixel_values[(896-block*128):(928-block*128)] = bottom_data[97:]

            ptats[block] = top_data[0]
            ptats[7-block] = bottom_data[0]

        pixel_values = np.reshape(pixel_values, (32, 32))
        return (pixel_values, ptats)

    def expose_block(self, block, blind=False, vdd=False):
        cmd = 0x09 + (block << 4)
        cmd = cmd + 0x02 if blind else cmd
        cmd = cmd + 0x04 if vdd else cmd

        self.write_register(REG_CONFIG, cmd)

    def query_capture(self):
        query = [I2C.Message([REG_STATUS]), I2C.Message([0x00], read=True)]
        self.i2c.transfer(self.address, query)
        
        return query[1].data[0]

    def block_capture_finished(self, block, blind, vdd):
        expected = 1 + (block << 4)
        expected = expected + 0x02 if blind else expected
        expected = expected + 0x04 if vdd else expected

        ans = self.query_capture()

        return expected == ans

    def eeprom_value_to_float(self, value):
        return struct.unpack('f', reduce(lambda a,b: a+b, [chr(v) for v in value]))[0]


def unsigned_to_signed_array(arr, bits=16):
    arr = [a - 2**bits if a >= 2**(bits-1) else a for a in arr]
    return arr


if __name__ == "__main__":
    dev = HTPA(0x1A)

    # should be run periodically. For instance from 10 to 10 seconds.
    dev.update_compensation_parameters()

    # 32x32 array of object temperatures in celsius
    # ambient temperature given in decikelvins
    temperatures, ta = dev.capture_temperatures()

    print("Ambient temperature: {}".format(ta))
    print("Temperatures: ")
    print(temperatures)

    dev.close()