#! /usr/bin/python3


# This is a client for the z906 soundsystem
# Most of the serial code is a reimplementation of https://github.com/zarpli/Logitech-Z906

import serial
import logging
import time

SERIAL_PORT = '/dev/ttyAMA0'
TIMEOUT = 5



class Z906Client():


    VOLUME_MAX          = 43

    # Command length
    STATUS_TOTAL_LENGTH = 23
    TEMP_TOTAL_LENGTH   = 10

    # Requests
    GET_TEMP            = 0x25
    GET_STATUS          = 0x34


    # Status fields
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
    STATUS_HEADPHONES       = 20
    STATUS_AUTO_STANDBY     = 21
    STATUS_CHECKSUM         = 23


    status = [ 0 ] * STATUS_TOTAL_LENGTH

    muted = False
    ser = None

    speaker_fields = {
            'main': STATUS_MAIN_LEVEL,
            'rear': STATUS_REAR_LEVEL,
            'center': STATUS_CENTER_LEVEL,
            'sub': STATUS_SUB_LEVEL }

    def __init__(self, serial_port=SERIAL_PORT):
        self.logger = logging.getLogger("Z906Client")
        self.ser = serial.Serial(serial_port, baudrate=57600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_ODD, stopbits=serial.STOPBITS_ONE, timeout=5)

    def __del__(self):
        if self.ser:
            self.ser.close()


    def _cksum(self, data):
        cksum = 0
        for b in data[1:-1]:
            cksum += b
        return 0x100 - (cksum & 0xFF)

    def request_ex(self, req_type, data):
        req = [ 0xAA, req_type, len(data) ]
        req.extend(data)
        req.append(0x0)
        req[-1] = self._cksum(req)
        self.logger.debug("Request : " + ' '.join('{:02x}'.format(x) for x in req))
        return self.request(req)


    def request(self, cmd):
        if not isinstance(cmd, list):
            cmd = [cmd]

        if self.ser.in_waiting > 0:
            self.logger.debug("Discarding " + str(self.ser.in_waiting) + " bytes of response")
        self.ser.reset_input_buffer()
        self.ser.write(bytes(cmd))

        ret = None

        while True:
            ret = bytearray(self.ser.read(1))
            if len(ret) == 0:
                self.logger.warning("No response from the AMP !")
                return None
            # Either single byte response or full len response
            if ret[0] == 0xAA: # We got an  extended response
                break
            else: # One byte response, let's see if there is more ...
                time.sleep(.1)
                self.logger.debug(("Response: {:02x}" .format(ret[0])))
                if self.ser.in_waiting == 0:
                    return ret

        # Only extended responses at this point
        ret.extend(bytearray(self.ser.read(2)))
        l = ret[2]
        ret.extend(bytearray(self.ser.read(l + 1)))

        cksum = self._cksum(ret)

        self.logger.debug("Response: " + ' '.join('{:02x}'.format(x) for x in ret) + " (cksum " + ( "OK" if cksum == ret[-1] else "INALID") + ")" )
        return ret

    def print_status(self):

        self.logger.debug("Status : " + ''.join('{:02x}'.format(x) for x in self.status))
        print("Levels : main " + str(self.status[self.STATUS_MAIN_LEVEL]) + "/43, center " + str(self.status[self.STATUS_CENTER_LEVEL]) + "/43, subwoofer " + str(self.status[self.STATUS_SUB_LEVEL]) + "/43, rear " + str(self.status[self.STATUS_REAR_LEVEL]) + "/43")
        print("Current input : " + str(self.status[self.STATUS_CURRENT_INPUT] + 1))
        print("Headphones : " + ("enabled" if self.status[self.STATUS_HEADPHONES] else "disabled"))


    def update(self):

        self.logger.debug("Updating status ...")
        ret = self.request(self.GET_STATUS)
        if len(ret) == 0:
            self.logger.critical("Unable to communicate with Z906 : read timeout")
            raise TimeoutError
        self.status = bytearray(ret)

    def level_up(self, spkr='main'):

        if spkr not in self.speaker_fields:
            raise ValueError("Invalid speaker provided")

        field = self.speaker_fields[spkr]

        cmd = 0
        if spkr == 'main':
            cmd = 0x08
        elif spkr == 'sub' or spkr == 'subwoofer':
            cmd = 0x0A
        elif spkr == 'center':
            cmd = 0x0C
        elif spkr == 'rear':
            cmd = 0x0E

        if self.status[field] == self.VOLUME_MAX:
            raise ValueError("Volume level for " + spkr + " already at maximum")

        ret = self.request(cmd)
        self.status[field] += 1
        self.logger.info("Level for " + spkr + " up to " + str(self.status[field]))


    def level_down(self, spkr='main'):

        if spkr not in self.speaker_fields:
            raise ValueError("Invalid speaker provided")

        cmd = 0
        field = self.speaker_fields[spkr]
        if spkr == 'main':
            cmd = 0x09
        elif spkr == 'sub' or spkr == 'subwoofer':
            cmd = 0x0B
        elif spkr == 'center':
            cmd = 0x0D
        elif spkr == 'rear':
            cmd = 0x0F

        if self.status[field] == 0:
            raise ValueError("Volume level for " + spkr + " already at minimum")

        ret = self.request(cmd)
        self.status[field] -= 1
        self.logger.info("Level " + spkr + " down to " + str(self.status[field]))

    def get_level(self, spkr='main'):

        if spkr not in self.speaker_fields:
            raise ValueError("Invalid speaker provided")

        field = self.speaker_fields[spkr]
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

        ret = self.request(cmd)

    def get_input(self):
        self.update()
        return self.status[self.STATUS_CURRENT_INPUT] + 1

    def mute(self, on):
        """
        Turn mute on or off.
        
        on: Boolean
        """
        if on:
            self.logger.debug("Muting")
            cmd = 0x38
        else:
            self.logger.debug("Unmuting")
            cmd = 0x39
        ret = self.request(cmd)
        self.muted = on

    def mute_toggle(self):
        """
        Toggle mute.
        """
        self.logger.debug("Toggling mute")
        self.mute(not self.muted)

    def is_muted(self):
        """
        Return mute status.
        """
        return self.muted

    def headphones(self, on):
        """
        Turn on or off the headphones/
        on: Boolean
        """
        if on:
            self.logger.debug("Switching to headphones")
            cmd = 0x10
        else:
            self.logger.debug("No headphones")
            cmd = 0x11
        ret = self.request(cmd)


    def effect(self, fx):
        """
        Set the effect for current input.
        Available effect: 3d, 2.1, 4.1, off.
        """

        cmd = 0
        if fx == "3d" or fx == "3D":
            cmd = 0x14
        elif fx == "4.1":
            cmd = 0x15
        elif fx == "2.1":
            cmd = 0x16
        elif fx == "off":
            cmd = 0x35
        else:
            raise ValueError("Unknown effect " + fx)
        ret = self.request(cmd)

    def temperature(self):
        """
        Get the temperature.
        """

        ret = self.request(0x25)
        if ret[1] != 0xC:
            print("Unable to read current temperature")

        print(str(ret[6]) + " C")

    def power_on(self):
        """
        Power on is achieved by turning off or on the headphones.
        """
        self.headphones(False)
        self.mute(False)

    def power_off(self):
        """
        Power off the Z906.
        """
        ret = self.request(0x37)

    def parse_cmd(self, cmd):

        cmd = cmd.split()

        if len(cmd) < 1:
            return

        commands = {
            "v": self._cmd_vol,
            "vol": self._cmd_vol,
            "volume": self._cmd_vol,
            "+": lambda x : self.level_up(),
            "-": lambda x : self.level_down(),
            "mute" : self._cmd_mute,
            "m" : self._cmd_mute,
            "input": self._cmd_input,
            "i": self._cmd_input,
            "status": lambda x: { self.update(), self.print_status() },
            "headphones": self._cmd_headphones,
            "h": self._cmd_headphones,
            "effect": self._cmd_effect,
            "fx": self._cmd_effect,
            "raw": self._cmd_raw,
            "temperature": lambda x: self.temperature(),
            "on": lambda x: self.power_on(),
            "off": lambda x: self.power_off(),
            }

        if cmd[0] in commands:
            commands[cmd[0]](cmd[1:])
        else:
            raise ValueError("Unknown command")

    def _cmd_raw(self, cmd):
        if len(cmd) < 1:
            raise ValueError("No command provided")

        if len(cmd) == 1: # Single byte reqyest
            req = int(cmd[0], base=16)
            print("Sending 0x{:02x}".format(req))
            self.request(req)
        else:
            t = int(cmd[0], base=16)
            data = []
            for c in cmd[1:]:
                data.append(int(c, base=16))
            print("Sending req with type 0x{:02x}".format(t) + " and data " + ' '.join('{:02x}'.format(x) for x in data))
            self.request_ex(t, data)

    def _cmd_input(self, cmd):
        if len(cmd) < 1:
            self.update()
            print("Current input : " + str(self.status[self.STATUS_CURRENT_INPUT] + 1))
            return

        self.select_input(int(cmd[0]))

    def _cmd_effect(self, cmd):
        if len(cmd) < 1:
            raise ValueError("No effect provided")
        self.effect(cmd[0])

    def _cmd_headphones(self, cmd):
        if len(cmd) < 1:
            self.update()
            print("Headphones : " + ("enabled" if self.status[self.STATUS_HEADPHONES] else "disabled"))
            return

        if cmd[0] == "on":
            self.headphones(True)
        elif cmd[0] == "off":
            self.headphones(False)
        elif cmd[0] == "toggle":
            self.update()
            self.headphones(not self.status[self.STATUS_HEADPHONES])
        else:
            raise ValueError("Unknown parameter")


    def _cmd_vol(self, cmd):

        if len(cmd) < 1:
            self.update()
            print("Levels : main " + str(self.status[self.STATUS_MAIN_LEVEL]) + "/43, center " + str(self.status[self.STATUS_CENTER_LEVEL]) + "/43, subwoofer " + str(self.status[self.STATUS_SUB_LEVEL]) + "/43, rear " + str(self.status[self.STATUS_REAR_LEVEL]) + "/43")
            return

        spkr = "main"
        speakers = [ "main", "sub", "subwoofer", "center", "rear" ]
        if len(cmd) == 2:
            if cmd[1] in speakers:
                spkr = cmd[1]
            else:
                raise ValueError("Unknown speaker " + cmd[1])

        if cmd[0] == "up":
            self.level_up(spkr)
        elif cmd[0] == "down":
            self.level_down(spkr)
        else:
            raise ValueError("Uknonwn argument to volume command : " + cmd[0])

    def _cmd_mute(self, cmd):
        if len(cmd) == 0:
            self.mute_toggle()
        elif cmd[0] == "on":
            self.mute(True)
        elif cmd[0] == "off":
            self.mute(False)
        else:
            raise ValueError("Unknown parameter to mute command " + cmd[0])


    def main_loop(self):


        while True:

            try:
                cmd = input("> ")
            except EOFError:
                print()
                break


            try:
                self.parse_cmd(cmd)
            except ValueError as e:
                print(e)


if __name__ == '__main__':

    import argparse
    argparser = argparse.ArgumentParser(description="Logitech Z906 client")
    argparser.add_argument('--port', '-p', dest='port', help='Z906 serial port', default=SERIAL_PORT)
    argparser.add_argument('--debug', '-d', dest='debug', help='Enable debugging', default=False, action='store_const', const=True)
    argparser.add_argument('--command', '-c', dest='cmd', help='Execute a single command', action='append', default=None)
    args = argparser.parse_args()


    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


    z906 = Z906Client(args.port)

    if not args.cmd:
        z906.update()
        z906.main_loop()
    else:
        z906.update()
        for cmd in args.cmd:
            z906.parse_cmd(cmd)
