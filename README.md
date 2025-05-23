# SLZB-07 integrations

## Hardware

* https://smlight.tech/product/slzb-07p7
* Chipset: CC2652P7
* Baud rate of the factory FW is 115200
* Firmware upgrade: https://smlight.tech/flasher/#SLZB-07

**IMPORTANT**: UPGRADE THE FIRMWARE. I struggled a lot with zigpy before I figured out my FW was older than what zigpy expected (facepalm).

## Sensors

### Aqara Temperature and humidity sensor T1

* Device name `lumi.sensor_ht.agl02`
* [Link](https://zigbee.blakadder.com/Aqara_WSDCGQ12LM.html)

## Dev setup

```
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

```
cp config.sample.toml config.toml
# Form your network (see below) then add the IEEE ids and give them names
```

## ZigPy

### Detour: radio types

* `ezsp`: Silicon Labs EmberZNet protocol (e.g., Elelabs, HUSBZB-1, Telegesis)
* `deconz`: dresden elektronik deCONZ protocol (e.g., ConBee I/II, RaspBee I/II)
* `znp`: Texas Instruments (e.g., CC253x, CC26x2, CC13x2)
* `zigate`: ZiGate Serial protocol (e.g., ZiGate USB-TTL, PiZiGate, ZiGate WiFi)
* `xbee`: Digi XBee ZB Coordinator Firmware protocol (e.g., Digi XBee Series 2, 2C, 3)

For some reason, SLZB-07p7 works with ezsp (bellows), but not with znp, even though it’s a TI chip… (https://smlight.tech/manual-slzb-07/ seems to confirm this, probably only a matter of firmware).

So the library we need is [zigpy/bellows](https://github.com/zigpy/bellows) specifically, but it turns out we need `zigpy-cli` to invoke eg. `energy-scan`.

### Forming a network

#### Initial setup

* Set the device: `export EZSP_DEVICE=/dev/ttyUSB0`
* Device info: `zigpy radio ezsp $EZSP_DEVICE info`
* Scan for interference: `zigpy radio ezsp $EZSP_DEVICE energy-scan`
* (Pick the most quiet channel)
* Change the channel (optional): `zigpy radio ezsp $EZSP_DEVICE change-channel -c <channel>`
* Reset the radio (optional): `zigpy radio --database zigbee.db ezsp $EZSP_DEVICE reset`
* **IMPORTANT**: you need to re-form the network after firmware upgrades!
* **IMPORTANT**: `zigpy radio ...` commands do NOT save anything into the `--database` for some reason, so I built my own form/permit commands:
  * Form a network: make sure `zigbee.db` does not exist in the dir, then run `./permit-join.py`

#### Adding a new device

* Allow pairing: run `./permit-join.py`, you have 4 minutes to pair (`Ctrl^C` to exit)
* Reset/pair your end devices in this timeframe. **IMPORTANT**: WAIT until all endpoints are discovered! Zigbee is SLOW.
* Note the `ieee` device id, and put it in your `config.toml`
* Verify the paired devices: `zigpy radio ezsp $EZSP_DEVICE backup` (look for the `devices` section at the end)

Note: the coordinator remembers joined devices, but `zigbee.db` has the network details, so we need to deploy that, too!

### Aqara notes

* Press and hold the button for 5+ seconds to pair
* Press once to wake it up (triggers a measurement)

## Links

* https://github.com/zigpy
* https://smlight.tech/manual-slzb-07/
* https://github.com/zigpy/zigpy-cli?tab=readme-ov-file#forming-a-network
* https://github.com/zigpy/zigpy/issues/1087
* https://github.com/zigpy/zigpy/blob/dev/CONTRIBUTING.md#the-zigpy-api
