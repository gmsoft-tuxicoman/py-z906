#!/usr/bin/python3

import dbus
import dbus.mainloop.glib
import logging

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)


class BTClient():
    
    def __init__(self, evtCallback = None):
        self.bus = dbus.SystemBus()
        self.transports = {}
        self.callback = evtCallback

        if not self.callback:
            self.callback = self._dummyCB

        self.logger = logging.getLogger("BTClient")


        self.bus.add_signal_receiver(self._interfaceAdded, dbus_interface='org.freedesktop.DBus.ObjectManager', signal_name = "InterfacesAdded")
        self.bus.add_signal_receiver(self._interfaceRemoved, dbus_interface='org.freedesktop.DBus.ObjectManager', signal_name = "InterfacesRemoved")
        self.bus.add_signal_receiver(self._propertiesChanged, dbus_interface='org.freedesktop.DBus.Properties', signal_name = "PropertiesChanged", path_keyword = "path")

        self.logger.info("Listening to bluetooth events ...")

    def _interfaceAdded(self, path, interface):
        if interface != 'org.bluez.MediaTransport1':
            return

        self.logger.info("Found new media transport : " + path)
        self.transports[path] = { 'volume': 0 }

    def _interfaceRemoved(self, path, interface):
        if interface != ' org.bluez.MediaTransport1':
            return 

        self.logger.info("Media transport gone : " + path)
        del self.transports[path]

    def _propertiesChanged(self, interface, changed, invalidated, path):
        if interface != 'org.bluez.MediaTransport1':
            return
        if path not in self.transports:
            self.logger.info("Found existing media transport : " + path)
            self.transports[path] = { 'volume': 0}

        if 'State' in changed:
            if changed['State'] == 'pending':
                self.logger.info("Playback started")
                self.callback("play")
            elif changed['State'] == 'idle':
                self.logger.info("Playback stopped")
                self.callback("pause")
   
        if 'Volume' in changed:
            vol = changed['Volume']
            self.logger.info("New volume : " + str(vol))
            self.callback("volume", vol)
            

    def mainloop(self):

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        mainloop = GLib.MainLoop()
        mainloop.run()
        return

    def _dummyCB(self, evt, val = None):
        if val:
            self.logger.debug("Event : " + evt + " (" + str(val) + ")")
        else:
            self.logger.debug("Event : " + evt)



if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    client = BTClient()
    client.mainloop()
