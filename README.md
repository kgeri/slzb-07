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

So the library we need is [zigpy/bellows](https://github.com/zigpy/bellows) specifically, but it turns out we need `zigpy-cli` to invoke eg. `energy-scan`.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
```

### Forming a network

* Set the device: `export EZSP_DEVICE=/dev/ttyUSB0`
* Device info: `zigpy radio ezsp $EZSP_DEVICE info`
* Scan for interference: `zigpy radio ezsp $EZSP_DEVICE energy-scan`
* (Pick the most quiet channel)
* Change the channel: `zigpy radio ezsp $EZSP_DEVICE change-channel -c <channel>`
* Form a network: `zigpy radio ezsp $EZSP_DEVICE form`
* Allow pairing: `zigpy -v radio ezsp $EZSP_DEVICE permit -t 60`
* (Reset/pair your end devices in this timeframe)
* Verify the paired devices: `zigpy radio --database srvu.db ezsp $EZSP_DEVICE backup` (look for the `devices` section at the end)

Note: the available options make you think you need a `--database`, but you actually don't. This particular coordinator remembers paired devices even when restarted.

## Links

* https://github.com/zigpy
* https://smlight.tech/manual-slzb-07/
* https://github.com/zigpy/zigpy-cli?tab=readme-ov-file#forming-a-network
* https://github.com/zigpy/zigpy/issues/452

