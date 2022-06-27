#! /usr/bin/python3

import cec
import logging


class CecClient:

    cecconfig = cec.libcec_configuration()
    lib = None

    def __init__(self, name):
        self.cecconfig.strDeviceName = name
        self.cecconfig.bActivateSource = 0
        self.cecconfig.deviceTypes.Add(cec.CEC_DEVICE_TYPE_AUDIO_SYSTEM)
        self.cecconfig.clientVersion = cec.LIBCEC_VERSION_CURRENT

        self.logger = logging.getLogger("CecClient")


    def open(self):
        self.lib = cec.ICECAdapter.Create(self.cecconfig)
        self.logger.info("libCEC version " + self.lib.VersionToString(self.cecconfig.serverVersion) + " loaded: " + self.lib.GetLibInfo())

        #search for adapters
        adapters = self.lib.DetectAdapters()
        if len(adapters) == 0:
            self.logger.critical("Not adapters found :-/")
            return False
        adapter = adapters[0]
        self.logger.debug("Found adapter " + adapter.strComName)
        self.lib.Open(adapter.strComName)


    def setCommandCallback(self, callback):
        self.cecconfig.SetCommandCallback(callback)

    def sendCommand(self, data):
        cmd = self.lib.CommandFromString(data)
        if not self.lib.Transmit(cmd):
            self.logger.warning("Error while sending CEC command")
        else:
            self.logger.debug("Sent : " + data)




if __name__ == '__main__':

    cecClient = CecClient("Z906")
    cecClient.open()

    while True:
        time.sleep(1)
