#! /usr/bin/python3


# This is a client for the z906 soundsystem
# Most of the serial code is a reimplementation of https://github.com/zarpli/Logitech-Z906

import serial
import logging

SERIAL_PORT = '/dev/ttyAMA0'



class Z906Client():


    VOLUME_MAX          = 43

    # Command length
    STATUS_TOTAL_LENGTH = 23
    TEMP_TOTAL_LENGTH   = 10

    # Requests
    GET_TEMP            = 0x25
    GET_STATUS          = 0x34


    # Status fields
    STATUS_STX              = 0
    STATUS_MODEL            = 1
    STATUS_LENGTH           = 2
    STATUS_MAIN_LEVEL       = 3
    STATUS_REAR_LEVEL       = 4
    STATUS_CENTER_LEVEL     = 5
    STATUS_SUB_LEVEL        = 6
    STATUS_CURRENT_INPUT    = 7
    STATUS_UNKNOWN          = 8
    STATUS_FX_INPUT_4       = 9
    STATUS_FX_INPUT_5       = 10
    STATUS_FX_INPUT_2       = 11
    STATUS_FX_INPUT_AUX     = 12
    STATUS_FX_INPUT_1       = 13
    STATUS_FX_INPUT_3       = 14
    STATUS_SPDIF_STATUS     = 15
    STATUS_SIGNAL_STATUS    = 16
    STATUS_VER_A            = 17
    STATUS_VER_B            = 18
    STATUS_VER_C            = 19
    STATUS_STANDBY          = 20
    STATUS_AUTO_STANDBY     = 21
    STATUS_CHECKSUM         = 22


    status = [ 0 ] * STATUS_TOTAL_LENGTH

    muted = False

    level_fields = {
            'main': STATUS_MAIN_LEVEL,
            'rear': STATUS_REAR_LEVEL,
            'center': STATUS_CENTER_LEVEL,
            'sub': STATUS_SUB_LEVEL }

    def __init__(self, serial_port=SERIAL_PORT):
        self.ser = serial.Serial(serial_port, baudrate=57600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_ODD, stopbits=serial.STOPBITS_ONE)
        self.logger = logging.getLogger("Z906Client")

    def __del__(self):
        self.pwm(False)
        self.ser.close()


    #def LRC(self, data):
    #    lrc = 0
    #    for b in data[1:-1]:
    #        lrc ^= b
    #    return lrc

    def request(self, cmd, rsp_len):
        if not isinstance(cmd, list):
            cmd = [cmd]

        self.ser.reset_input_buffer()
        self.ser.write(bytes(cmd))

        return self.ser.read(size=rsp_len)

    def print_status(self):

        print("Status : " + ''.join('{:02x}'.format(x) for x in self.status))
        print("STX      : " + str(self.status[self.STATUS_STX]))
        print("Model    : " + str(self.status[self.STATUS_MODEL]))
        print("Status len: " + str(self.status[self.STATUS_LENGTH]))

        print("Levels : main(" + str(self.status[self.STATUS_MAIN_LEVEL]) + "), center(" + str(self.status[self.STATUS_CENTER_LEVEL]) + "), subwoofer(" + str(self.status[self.STATUS_SUB_LEVEL]) + "), rear(" + str(self.status[self.STATUS_REAR_LEVEL]) + ")")
        print("Current input : " + str(self.status[self.STATUS_CURRENT_INPUT] + 1))
        print("Version : " + str(self.status[self.STATUS_VER_C] + 10 * self.status[self.STATUS_VER_B] + 100 * self.status[self.STATUS_VER_A]))


        #chksum = self.LRC(self.status)
        #print("Checksum : " + ("OK" if chksum == self.status[self.STATUS_CHECKSUM] else "Invalid") + " " + str(chksum))


    def update(self):

        ret = self.request(self.GET_STATUS, self.STATUS_TOTAL_LENGTH)
        self.status = bytearray(ret)

        #self.print_status()


    def level_up(self, level='main'):

        if level not in self.level_fields:
            raise ValueError("Invalid level provided")

        field = self.level_fields[level]

        cmd = 0
        if level == 'main':
            cmd = 0x08
        elif level == 'sub' or level == 'subwoofer':
            cmd = 0x0A
        elif level == 'center':
            cmd = 0x0C
        elif level == 'rear':
            cmd = 0x0E

        if self.status[field] == self.VOLUME_MAX:
            raise ValueError("Volume level for " + level + " already at maximum")

        ret = self.request(cmd, 1)
        self.status[field] += 1
        self.logger.debug("Level " + level + " up to " + str(self.status[field]))


    def level_down(self, level='main'):

        if level not in self.level_fields:
            raise ValueError("Invalid level provided")

        cmd = 0
        field = self.level_fields[level]
        if level == 'main':
            cmd = 0x09
        elif level == 'sub' or level == 'subwoofer':
            cmd = 0x0B
        elif level == 'center':
            cmd = 0x0D
        elif level == 'rear':
            cmd = 0x0F

        if self.status[field] == 0:
            raise ValueError("Volume level for " + level + " already at minimum")

        ret = self.request(cmd, 1)
        self.status[field] -= 1
        self.logger.debug("Level " + level + " down to " + str(self.status[field]))

    def get_level(self, level='main'):

        if level not in self.level_fields:
            raise ValueError("Invalid level provided")

        field = self.level_fields[level]
        return self.status[field]


    def select_input(self, input_num):
        """
        Select the input either by number or by name.
        
        input_num: input number [1-6] or 'aux'
        """
        cmd = 0
        if input_num == 1:
            cmd = 0x02
        elif input_num == 2:
            cmd = 0x05
        elif input_num == 3:
            cmd = 0x03
        elif input_num == 4:
            cmd = 0x04
        elif input_num == 5:
            cmd = 0x06
        elif input_num == 'aux' or input_num == 6:
            cmd = 0x07

        if cmd == 0:
            raise ValueError("Invalid input number provided")

        ret = self.request(cmd, 1)

    def mute(self, on):
        """
        Turn mute on or off.
        
        on: Boolean
        """
        if on:
            cmd = 0x38
        else:
            cmd = 0x39
        ret = self.request(cmd, 1)
        self.muted = on

    def mute_toggle(self):
        """
        Toggle mute.
        """
        self.mute(not self.muted)

    def is_muted(self):
        """
        Return mute status.
        """
        return self.muted

    def pwm(self, on):
        """
        Turn on or off the power.
        Unmute as well when turning on

        on: Boolean
        """
        if on:
            self.logger.debug("Turning on Z906")
            cmd = 0x11
        else:
            self.logger.debug("Turning off Z906")
            cmd = 0x10
        ret = self.request(cmd, 1)
        if on:
            self.mute(False)



    def main_loop(self):


        while True:

            status = self.ser.read(size=1)
            print(status)


if __name__ == '__main__':

    z906 = Z906Client()
    z906.update()
    z906.pwm(True)
    z906.select_input(1)
    z906.mute(False)
    z906.level_up()
    z906.update()
    z906.main_loop()
