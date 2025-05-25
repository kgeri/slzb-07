#!/usr/bin/env python3

from bellows.zigbee.application import ControllerApplication
from prometheus_async.aio.web import start_http_server
from prometheus_client.core import Gauge, REGISTRY
from zigpy.device import Device
from zigpy.endpoint import Endpoint
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import PressureMeasurement, RelativeHumidity, SoilMoisture, TemperatureMeasurement
import asyncio
import logging
import os
import time
import tomllib
import traceback
import zhaquirks


class MainListener:
    '''
    Contains callbacks that zigpy will call whenever something happens.
    Look for `listener_event` in the Zigpy source or just look at the logged warnings.
    '''

    _device_id_to_device_name: dict[str, str]
    _temp_celsius: Gauge
    _humidity_pcnt: Gauge
    _battery_pcnt: Gauge
    _soil_moisture_pct: Gauge

    def __init__(self, devices):
        self._device_id_to_device_name = {}
        self._temp_celsius = Gauge('temp_celsius', 'Temperature (C)', ['location'])
        self._humidity_pcnt = Gauge('humidity_pcnt', 'Relative humidity (%)', ['location'])
        self._battery_pcnt = Gauge('battery_pcnt', 'Remaining battery (%)', ['location'])
        self._soil_moisture_pct = Gauge('soil_moisture_pct', 'Soil moisture (%)', ['location'])
        for device in devices:
            device_id: str = device['device_id']
            device_name: str = device['name']
            self._device_id_to_device_name[device_id] = device_name
    
    def handle_message(self,
                       dev: Device,
                       profile_id: int,
                       cluster_id: int,
                       src_ep: int,
                       dst_ep: int,
                       data: bytes):
            logging.info(f'handle_message: device={dev}, src_ep={src_ep}, dst_ep={dst_ep}, data={data}')

            device_id = str(dev.ieee)
            if device_id not in self._device_id_to_device_name:
                logging.warning(f'Device not configured: {dev}')
                return
            
            device_name = self._device_id_to_device_name[device_id]
            
            # Reading input clusters
            for ep in dev.endpoints.values():
                if not isinstance(ep, Endpoint): continue
                for clus in ep.in_clusters.values():
                    try:
                        match clus:
                            # Generic ones
                            case PressureMeasurement():
                                pressure_kPa = clus.get('measured_value') / 1000
                                logging.info(f'[{device_name}] pressure_kPa={pressure_kPa}')
                            
                            case RelativeHumidity():
                                humidity_pcnt = clus.get('measured_value') / 100
                                self._humidity_pcnt.labels(location = device_name).set(humidity_pcnt)
                                logging.info(f'[{device_name}] humidity_pcnt={humidity_pcnt}')

                            case TemperatureMeasurement():
                                temp_c = clus.get('measured_value') / 100
                                self._temp_celsius.labels(location = device_name).set(temp_c)
                                logging.info(f'[{device_name}] temp_celsius={temp_c}')
                            
                            case SoilMoisture():
                                soil_moisture_pct = clus.get('measured_value') / 100
                                self._soil_moisture_pct.labels(location = device_name).set(soil_moisture_pct)
                                logging.info(f'[{device_name}] soil_moisture_pct={soil_moisture_pct}')

                            case PowerConfiguration():
                                battery_pcnt = clus.get('battery_percentage_remaining')
                                if battery_pcnt: # Note: for some crazy reason, Aqara and Tuya quirks both do an x2 on the percentage
                                    battery_pcnt = battery_pcnt / 2
                                    self._battery_pcnt.labels(location = device_name).set(battery_pcnt)
                                logging.info(f'[{device_name}] battery_pcnt={battery_pcnt}')

                            case _: logging.info(f'Unknown Cluster: {clus}')
                    except:
                        traceback.print_exc()
                        return

async def main():
    # Logging config
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%dT%H:%M:%SZ')
    logging.Formatter.converter = time.gmtime

    # Registry reset (to avoid exposing Python runtime metrics which I don't care about)
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)

    # Config load
    with open('config.toml', 'rb') as f:
        config = tomllib.load(f)

    ezsp_device = config.get('ezsp_device', '/dev/ttyUSB0')
    metrics_port = config.get('metrics_port', 9102)
    devices = config['devices']

    app: ControllerApplication|None = None
    try:
        # ZHA Quirks (for Tuya)
        zhaquirks.setup()

        # Radio init
        logging.info(f'Listening on radio: {ezsp_device}, devices={devices}')
        app = await ControllerApplication.new(config={
            'database_path': 'zigbee.db',
            'device': {
                'path': ezsp_device,
            }
        }, auto_form=False, start_radio=True) # type: ignore
        app.add_listener(MainListener(devices)) # type: ignore

        # Prometheus server start
        await start_http_server(addr='0.0.0.0', port=metrics_port)
        logging.info(f'Metrics exporter listening on 0.0.0.0:{metrics_port}')

        await asyncio.get_running_loop().create_future()
    except:
        traceback.print_exc()
        logging.info('Shutting down app...')
        if app: await app.shutdown()
        logging.info('Exiting.')
        os._exit(1) # This seems to be the only way to kill this f*$1ng Python process with asyncio...

if __name__ == '__main__':
    asyncio.run(main())
