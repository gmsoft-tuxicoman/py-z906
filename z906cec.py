#! /usr/bin/python3

import cecclient
import z906client
import time
import traceback
import argparse
import logging


argparser = argparse.ArgumentParser(description="Logitech Z906 CEC translator")
argparser.add_argument('--debug', '-d', dest='debug', help='Enable debugging', default=False, action='store_const', const=True)
argparser.add_argument('--port', '-P', dest='port', help='Z906 serial port', default=z906client.SERIAL_PORT)
argparser.add_argument('--input', '-i', dest='input', help='Z906 input to use (1-6)', default=1, type=int)
argparser.add_argument('--disable', '-D', dest='disabled', help='Disable ARC for certain HDMI ports', action='append', type=int)


class Z906Cec():

    disable_hdmi_dports = []
    z906 = None
    cecClient = None
    enabled = True

    logger = logging.getLogger("Z906Cec")


    def __init__(self, z906_port, z906_input):
    
        # Init the Z906
        self.logger.info("Connecting to Z906 ...")
        self.z906 = z906client.Z906Client(z906_port)
        self.z906.update()
        self.z906.select_input(z906_input)
        self.logger.debug("Connected to Z906")
        

        # Init CEC
        self.logger.info("Initiating CEC ...")
        self.cecClient = cecclient.CecClient("Z906")
        self.cecClient.setCommandCallback(self._cecCallback)
        self.cecClient.open()
        self.logger.debug("CEC initialized")

    
        self.logger.info("Ready !")
    def setDisabledPorts(self, disabled_hdmi_ports):
        if disabled_hdmi_ports == None:
            disabled_hdmi_ports = []
        self.disabled_hdmi_ports = disabled_hdmi_ports

    def _cecCallback(self, cmd):

        cmd=cmd[3:]
        self.logger.debug("Got CEC command " + cmd)

        # Key presset event
        if cmd.startswith("05:44:"):
            # Parse key press
            key = cmd[6:]
            if key == '41':
                self.logger.debug("Received key : Volume up")
                self.z906.level_up()
            elif key == '42':
                self.logger.debug("Received key : Volume down")
                self.z906.level_down()
            elif key == '43':
                self.logger.debug("Received key : Mute")
                self.z906.mute_toggle()
            else:
                return

            mute = z906.is_muted()
            level = z906.get_level()

            #status = int(100.0 / (z906.VOLUME_MAX + 1) * level)
            status = int(level)
            if mute:
                status += 0x80

            cmd = "50:7A:{:02x}".format(status)
            self.cecClient.sendCommand(cmd)

        # ARC start
        elif cmd == "05:c3":
            self.logger.debug("Received : ARC start")
            if self.enabled:
                self.z906.pwm(True)

        # ARC end
        elif cmd == "05:c4":
            self.logger.debug("Received : ARC stop")
            self.z906.pwm(False)

        # TV in standby
        elif cmd == "0f:36":
            # Standby
            self.logger.debug("Received : TV Standby")
            self.z906.pwm(False)

        # Get CEC Version
        elif cmd == "05:9f":
            self.logger.debug("Received : Get CEC Version")
            self.cecClient.send("05:9E:04")


        # Report audio status
        elif cmd == "05:7d":
            if self.enabled:
                self.cecClient.sendCommand("50:7e:01")
            else:
                self.cecClient.sendCommand("50:7e:00")

        elif cmd == "05:8f":
            cecClient.sendCommand("50:90:00")


        # System audio mode request
        elif cmd == "05:70:00:00":
            if self.enabled:
                self.ecClient.sendCommand("50:72:01")
            else:
                self.ecClient.sendCommand("50:72:00")

        # Source change
        elif cmd[3:].startswith("82:"):
            self.logger.debug("Received source change to HDMI port " + cmd[4:])
            port = int(cmd[4:5])
            if port in self.disabled_hdmi_ports:
                self.enabled = False

            if self.enabled:
                self.logger.info("CEC ARC enabled")
                self.cecClient.sendCommand("50:72:01")
                self.z906.pwm(True)
            else:
                self.logger.info("CEC ARC disabled")
                self.cecClient.sendCommand("50:72:00")
                self.z906.pwm(False)
            
        
                
if __name__ == "__main__":
    args = argparser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    z906cec = Z906Cec(args.port, args.input)
    z906cec.setDisabledPorts(args.disabled)


while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break
