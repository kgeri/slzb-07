#!/usr/bin/env python3

from bellows.zigbee.application import ControllerApplication
from prometheus_async.aio.web import start_http_server
from prometheus_client.core import Gauge, REGISTRY
from zigpy.zcl.clusters.measurement import PressureMeasurement, RelativeHumidity, TemperatureMeasurement
import asyncio
import logging
import os
import time
import tomllib
import traceback
import zigpy


class MainListener:
    '''
    Contains callbacks that zigpy will call whenever something happens.
    Look for `listener_event` in the Zigpy source or just look at the logged warnings.
    '''

    _device_id_to_device_name: dict[str]
    _temp_celsius: Gauge
    _humidity_pcnt: Gauge

    def __init__(self, devices):
        self._device_id_to_device_name = {}
        self._temp_celsius = Gauge('temp_celsius', 'Temperature (C)', ['location'])
        self._humidity_pcnt = Gauge('humidity_pcnt', 'Relative humidity (%)', ['location'])
        for device in devices:
            device_id: str = device['device_id']
            device_name: str = device['name']
            self._device_id_to_device_name[device_id] = device_name
    
    def handle_message(self,
                       dev: zigpy.device.Device,
                       profile_id: int,
                       cluster_id: int,
                       src_ep: int,
                       dst_ep: int,
                       data: bytes):
        logging.debug(f'handle_message: device={dev}, src_ep={src_ep}, dst_ep={dst_ep}, data={data}')

        for ep in dev.endpoints.values():
            if type(ep) != zigpy.endpoint.Endpoint: continue
            for clus in ep.in_clusters.values():
                match clus:
                    case PressureMeasurement(): pressure_kPa = clus.get('measured_value') / 1000
                    case RelativeHumidity(): humidity_pcnt = clus.get('measured_value') / 100
                    case TemperatureMeasurement(): temp_c = clus.get('measured_value') / 100
                    case _: logging.debug(f'Unknown: {clus}')
        
        device_id = str(dev.ieee)
        if device_id in self._device_id_to_device_name:
            device_name = self._device_id_to_device_name[device_id]
            self._temp_celsius.labels(location = device_name).set(temp_c)
            self._humidity_pcnt.labels(location = device_name).set(humidity_pcnt)
            logging.info(f'Reported name={device_name}, device_id={device_id}, pressure={pressure_kPa}kPa, humidity={humidity_pcnt}%, temp={temp_c}C')
        else:
            logging.warning(f'Device not configured: {dev} (pressure={pressure_kPa}kPa, humidity={humidity_pcnt}%, temp={temp_c}C)')

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

    app: ControllerApplication = None
    try:
        # Radio init
        logging.info(f'Listening on radio: {ezsp_device}, devices={devices}')
        app = await ControllerApplication.new(config={
            'database_path': 'zigbee.db',
            'device': {
                'path': ezsp_device,
            }
        }, auto_form=False, start_radio=True)
        app.add_listener(MainListener(devices))

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
