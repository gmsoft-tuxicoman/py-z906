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
argparser.add_argument('--address', '-a', dest='enabled', help='Enabled ARC only for certain HDMI ports', action='append')


class Z906Cec():

    enabled_hdmi_ports = None
    z906 = None
    cecClient = None
    logger = logging.getLogger("Z906Cec")


    def __init__(self, z906_port, z906_input, enabled_ports = None):
    
        self.enabled_hdmi_ports = enabled_ports
        self.logger.info("Enabled HDMI ports : " + str(enabled_ports))

        # Init the Z906
        self.logger.info("Connecting to Z906 ...")
        self.z906 = z906client.Z906Client(z906_port)
        self.z906.update()
        self.z906.select_input(z906_input)
        self.logger.debug("Connected to Z906")
        

        # Init CEC
        self.logger.info("Initiating CEC ...")
        self.cecClient = cecclient.CecClient("Z906")
        self.cecClient.open()
        self.logger.debug("CEC initialized")
        self.cecClient.setEventCallback(self._cecCallback)

    
        self.logger.info("Ready !")

    def _cecCallback(self, evt):


        self.logger.debug("Got event " + evt)

        if evt == "level_up":
            self.z906.level_up()
            self.cecClient.reportAudioStatus(z906.get_level(), z906.is_muted())
        elif evt == "level_down":
            self.z906.level_down()
            self.cecClient.reportAudioStatus(z906.get_level(), z906.is_muted())
        elif evt == "mute":
            self.z906.mute_toggle()
            self.cecClient.reportAudioStatus(z906.get_level(), z906.is_muted())
        elif evt == "give_audio_status":
            self.cecClient.reportAudioStatus(z906.get_level(), z906.is_muted())


        elif evt == "arc_start":
            if self.cecClient.is_enabled():
                self.z906.power_on()
        elif evt == "arc_stop":
            if self.cecClient.is_enabled():
                self.z906.power_off()

        elif evt == "standby":
            self.z906.power_off()

        elif evt == "src_changed":
            src_port = self.cecClient.get_src_port()
            self.logger.info("Source changed to " + src_port)
            if not self.enabled_hdmi_ports:
                return
            
            for p in self.enabled_hdmi_ports:
                if src_port.startswith(p):
                    self.cecClient.enable()
                    return
            self.cecClient.disable()

                
if __name__ == "__main__":
    args = argparser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    z906cec = Z906Cec(args.port, args.input, args.enabled)


while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break
