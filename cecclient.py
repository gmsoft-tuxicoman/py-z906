#! /usr/bin/python3

import cec
import logging


class CecClient:

    cecconfig = cec.libcec_configuration()
    lib = None
    evtCallback = None
    enabled = True

    # Assume default source is TV
    src_port = "0.0.0.0"

    def __init__(self, name):
        self.cecconfig.strDeviceName = name
        self.cecconfig.bActivateSource = 0
        self.cecconfig.deviceTypes.Add(cec.CEC_DEVICE_TYPE_AUDIO_SYSTEM)
        self.cecconfig.clientVersion = cec.LIBCEC_VERSION_CURRENT
        self.cecconfig.SetCommandCallback(self._cmdCallback)

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

    def reportAudioStatus(self, level, mute):

        status = int(level)
        if mute:
            status += 0x80
        cmd = "7A:{:02x}".format(status)
        self.sendCommand(cmd)

    def enable(self):
        if self.enabled:
            return

        self.enabled = True
        self.logger.info("Enabling CEC ARC")

        # Power on
        self.sendCommand("90:00")
        # System audio mode status on
        self.sendCommand("72:01")
        self.logger.info("CEC ARC enabled")

    def disable(self):
        if not self.enabled:
            return

        self.enabled = False
        self.logger.info("Disabling CEC ARC")

        # Power off
        self.sendCommand("90:01")
        # System audio mode status off
        self.sendCommand("72:00")
        self.logger.info("CEC ARC disabled")

    def is_enabled(self):
        return self.enabled

    def get_src_port(self):
        return self.src_port


    def _cmdCallback(self, cmd):

        cmd=cmd[3:]
        self.logger.debug("Got CEC command " + cmd)

        # Discard source and dest
        if cmd[1] != 'f' and cmd[1] != '5':
            self.logger.debug("Ignoring command as it's not destined for broadcast or audio-system")
            return

        src = cmd[0]
        cmd = cmd[3:]

        # Key presset event
        if cmd.startswith("44:"):
            # Parse key press
            key = cmd[3:]
            if key == '41':
                self.logger.debug("Received key : Volume up")
                self.evtCallback("level_up")
            elif key == '42':
                self.logger.debug("Received key : Volume down")
                self.evtCallback("level_down")
            elif key == '43':
                self.logger.debug("Received key : Mute")
                self.evtCallback("mute")
            else:
                return

        # ARC start
        elif cmd == "c3":
            self.logger.debug("Received : ARC start")
            self.evtCallback("arc_start")

        # ARC end
        elif cmd == "c4":
            self.logger.debug("Received : ARC stop")
            self.evtCallback("arc_stop")

        # TV in standby
        elif cmd == "36":
            # Standby
            self.logger.debug("Received : TV Standby")
            self.evtCallback("standby")

        # Get CEC Version
        elif cmd == "9f":
            self.logger.debug("Received : Get CEC Version")
            self.send("9E:05", dst=src) # Version 1.4

        # Give audio status
        if cmd == "71":
            self.logger.debug("Received : Give audio status")
            self.evtCallback("give_audio_status")


        # Give system audio mode status
        elif cmd == "7d":
            if self.enabled:
                # Audio status on
                self.sendCommand("7e:01", dst=src)
            else:
                # Audio status off
                self.sendCommand("7e:00", dst=src)

        # Give power status
        elif cmd == "8f":
            if self.enabled:
                # Power on
                sendCommand("90:00", dst=src)
            else:
                # Standby
                sendCommand("90:01", dst=src)


        # System audio mode request
        elif cmd.startswith("70"):
            if self.enabled:
                self.sendCommand("72:01", dst=src)
            else:
                self.sendCommand("72:00", dst=src)

        # One touch play active source
        elif cmd.startswith("82:"):
            src_port = cmd[3] + '.' + cmd[4] + '.' + cmd[6] + '.' + cmd[7]
            self.logger.debug("Received one touch play on HDMI port " + src_port)
            if src_port != self.src_port:
                self.src_port = src_port
                self.evtCallback("src_changed")

        # Routing change
        elif cmd.startswith("80:"):
            src_port = cmd[9] + '.' + cmd[10] + '.' + cmd[12] + '.' + cmd[13]
            self.logger.debug("Received routing change to new address " + src_port)
            if src_port != self.src_port:
                self.src_port = src_port
                self.evtCallback("src_changed")

    def sendCommand(self, data, src='5', dst='0'):
        cmd_str = src + dst + ':' + data
        cmd = self.lib.CommandFromString(src + dst + ':' + data)
        if not self.lib.Transmit(cmd):
            self.logger.warning("Error while sending CEC command")
        else:
            self.logger.debug("Sent : " + data)


    def setEventCallback(self, callback):
        self.evtCallback = callback


if __name__ == '__main__':

    cecClient = CecClient("Z906")
    cecClient.open()

    while True:
        time.sleep(1)
