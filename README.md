# py-z906
Python API to control the Logitech Z906

This project provide a client for the serial interface of the Logitech Z906.  
For pinout details, see this project : https://github.com/zarpli/Logitech-Z906 or this one : https://github.com/nomis/logitech-z906/blob/main/interface.rst

## z906client.py
This client provides a CLI interface to the Z906.
It can be used either interactively or using the -c argument to provide the command to run.
This is usefull if you want to use it to bind the volume button on your keyboad.

Examples:  
Volume up : ```z906client.py -p /dev/ttyUSB0 -c 'mute off' -c '+'```  
Volume down : ```z906client.py -p /dev/ttyUSB0 -c 'mute off' -c '-'```  
Mute : ```z906client.py -p /dev/ttyUSB0 -c 'mute'```  
Toggle headphoness : ```z906client.py -p /dev/ttyUSB0 -c 'mute off' -c 'headphones toggle'```  

Interactive example :

```# ~/z906 $ ./z906client.py -p /dev/ttyUSB0
> headphones on
> status
Levels : main 11/43, center 22/43, subwoofer 21/43, rear 23/43
Current input : 1
Headphones : enabled
> h off
> vol up
INFO:Z906Client:Level for main up to 12
> off
>
```

| Commands | Description |
| --- | --- |
| `+` | Turn main volume up |
| `-` | Turn main volume down |
| `vol up` | Turn main volume up |
| `vol down` | Turn main volume down |
| `vol up/down center` | Turn center volume up/down |
| `vol up/down rear` | Turn rear volume up/down |
| `vol up/down sub/subwoofer` | Turn subwoofer volume up/down |
| `vol` | Show current volume levels |
| `mute` | Toggle mute (only works if mute status is known) |
| `mute on/off` | Turn mute on/off |
| `input [1-5]` | Select the source input |
| `status` | Show current status of Z906 |
| `on` | Turn on the Z906 |
| `off` | Turn off the Z906 |
| `temperature` | Show the Z906 temperature |
| `effect 3d/4.1/2.1/off` | Set the effect on the current input |
| `v` | Alias for vol |
| `volume` | Alias for vol |
| `fx` | Alias for effect |
| `i` | Alias for input |
| `m` | Alias for mute |
| `raw` | Allows to send raw command to the Z906, see code for more details |


## z906cec.py
This client translate CEC commands from a TV directly to the Z906 and emulates a HDMI amplifier with CEC-ARC capabilities.  
**It does not receive the audio, only controls the volume !**  
This allows you to plug your TV or player to the Z906 via SPDIF or analog input and control the volume and mute via the TV remote.
This works especially well on RPI which have both a UART port on the GPIO header and a CEC input over HDMI.  
**You must connect the HDMI cable on the HDMI ARC port of the TV.**

If you only want to use the Z906 for certain HDMI ports you can specify the `-a <hdmi-port-number>` for each port you want to use the Z906. When another HDMI port is in use on TV, the CEC-ARC will be disabled and allow the TV speakers to be used.
