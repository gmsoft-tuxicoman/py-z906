#! /usr/bin/python3

import btclient
import z906client
import logging
import argparse


argparser = argparse.ArgumentParser(description="Logitech Z906 BT translator")
argparser.add_argument('--debug', '-d', dest='debug', help='Enable debugging', default=False, action='store_const', const=True)
argparser.add_argument('--port', '-P', dest='port', help='Z906 serial port', default=z906client.SERIAL_PORT)
argparser.add_argument('--input', '-i', dest='input', help='Z906 input to use (1-6)', default=1, type=int)


class Z906BT():

    z906 = None
    bt = None
    last_input = 1
    logger = logging.getLogger("Z906BT")


    def __init__(self, z906_port, z906_input):

        self.logger.info("Connecting to Z906 ...")
        self.z906 = z906client.Z906Client(z906_port)
        self.logger.debug("Connected to Z906")

        self.bt = btclient.BTClient(self.evtCallback)

    def __del__(self):
        self.logger.info("Powering off Z906 ...")
        self.z906.power_off()

    def evtCallback(self, evt, val = None):
        if evt == "play":
            self.last_input = self.z906.get_input()
            self.z906.power_on()
        elif evt == "pause":
            self.z906.select_input(self.last_input)
            self.z906.power_off()
        elif evt == "volume":
            
            # There is no way to directly set the level
            # so we need to increase or decrease the volume
            # until we're at the right value

            self.z906.update()
            cur_vol = self.z906.get_level()
            new_vol = int(43.0 / 127.0 * float(val))
            self.logger.debug("BT Volume : " + str(val) + " Z906 Volume : " + str(new_vol))
            if new_vol > cur_vol:
                for i in range(new_vol - cur_vol):
                    self.z906.level_up()
            else:
                for i in range(cur_vol - new_vol):
                    self.z906.level_down()
            

    def mainloop(self):
        self.bt.mainloop()

if __name__ == "__main__":
    args = argparser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


    z906bt = Z906BT(args.port, args.input)

    try:
        z906bt.mainloop()
    except KeyboardInterrupt:
        pass

    
