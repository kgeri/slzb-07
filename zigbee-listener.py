#!/usr/bin/env python3

from bellows.zigbee.application import ControllerApplication
from zigpy.zcl.clusters.measurement import PressureMeasurement, RelativeHumidity, TemperatureMeasurement
import asyncio
import logging
import time
import zigpy


class MainListener:
    '''
    Contains callbacks that zigpy will call whenever something happens.
    Look for `listener_event` in the Zigpy source or just look at the logged warnings.
    '''

    # Application

    def raw_device_initialized(self, dev):
        logging.debug(f'raw_device_initialized {dev}')

    def device_initialized(self, dev):
        logging.info(f'device_initialized name={dev.name}, ieee={dev.ieee}, model={dev.model}, endpoints={dev.endpoints}')

    def device_removed(self, dev):
        logging.info(f'device_removed: {dev.name}')

    def device_joined(self, dev: zigpy.device.Device):
        logging.info(f'device_joined: name={dev.name}, ieee={dev.ieee}, model={dev.model}')
    
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
        logging.info(f'pressure={pressure_kPa}kPa, humidity={humidity_pcnt}%, temp={temp_c}C')

async def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%dT%H:%M:%SZ')
    logging.Formatter.converter = time.gmtime

    app = await ControllerApplication.new(config={
        'database_path': 'zigbee.db',
        'device': {
            'path': '/dev/ttyUSB0',
        }
    }, auto_form=True)
    
    listener = MainListener()
    app.add_listener(listener)

    logging.info('Listening...')
    try:
        await asyncio.get_running_loop().create_future()
    except asyncio.exceptions.CancelledError:
        logging.info('Shutting down...')
        await app.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
