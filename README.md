# SLZB-07 integrations

## Hardware

* https://smlight.tech/product/slzb-07p7
* Chipset: CC2652P7
* Baud rate of the factory FW is 115200

## ZigPy

### Detour: radio types

* `ezsp`: Silicon Labs EmberZNet protocol (e.g., Elelabs, HUSBZB-1, Telegesis)
* `deconz`: dresden elektronik deCONZ protocol (e.g., ConBee I/II, RaspBee I/II)
* `znp`: Texas Instruments (e.g., CC253x, CC26x2, CC13x2)
* `zigate`: ZiGate Serial protocol (e.g., ZiGate USB-TTL, PiZiGate, ZiGate WiFi)
* `xbee`: Digi XBee ZB Coordinator Firmware protocol (e.g., Digi XBee Series 2, 2C, 3)

For some reason, SLZB-07p7 works with ezsp (bellows), but not with znp, even though it’s a TI chip… (https://smlight.tech/manual-slzb-07/ seems to confirm this, probably only a matter of firmware).

So the library we need is [zigpy/bellows](https://github.com/zigpy/bellows) specifically.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
```

### Scanning

```
export EZSP_DEVICE=/dev/ttyUSB0
bellows -b 115200 info
```

## Links

* https://github.com/zigpy
* https://smlight.tech/manual-slzb-07/

