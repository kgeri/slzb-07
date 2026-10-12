#!/usr/bin/env python3

from aiohttp import web
from bellows.zigbee.application import ControllerApplication
from prometheus_async.aio.web import server_stats
from prometheus_client.core import Gauge, REGISTRY
from zigpy.device import Device
from zigpy.endpoint import Endpoint
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import PressureMeasurement, RelativeHumidity, SoilMoisture, TemperatureMeasurement
from zha.quirks import DEVICE_REGISTRY
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
    _last_seen_ts: Gauge
    _last_seen_unix: dict[str, float]

    def __init__(self, devices):
        self._device_id_to_device_name = {}
        self._temp_celsius = Gauge('temp_celsius', 'Temperature (C)', ['location'])
        self._humidity_pcnt = Gauge('humidity_pcnt', 'Relative humidity (%)', ['location'])
        self._battery_pcnt = Gauge('battery_pcnt', 'Remaining battery (%)', ['location'])
        self._soil_moisture_pct = Gauge('soil_moisture_pct', 'Soil moisture (%)', ['location'])
        self._last_seen_ts = Gauge('last_seen_timestamp_seconds', 'Unix timestamp of the last Zigbee message received from the device', ['location'])
        self._last_seen_unix = {}
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
            device_id = str(dev.ieee)
            if device_id not in self._device_id_to_device_name:
                logging.warning(f'Device not configured: {dev}')
                return

            device_name = self._device_id_to_device_name[device_id]
            now = time.time()
            self._last_seen_unix[device_name] = now
            self._last_seen_ts.labels(location = device_name).set(now)
            logging.info(f'handle_message: device={dev}, src_ep={src_ep}, dst_ep={dst_ep}, data={data}')

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

    def device_status(self) -> list[dict]:
        now = time.time()
        status = []
        for device_id, device_name in self._device_id_to_device_name.items():
            last_seen = self._last_seen_unix.get(device_name)
            status.append({
                'name': device_name,
                'device_id': device_id,
                'last_seen': last_seen,
                'age_seconds': None if last_seen is None else round(now - last_seen, 1),
            })
        return status

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
    admin_port = config.get('admin_port', 9103)
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
        }, auto_form=False, start_radio=True, device_resolver=DEVICE_REGISTRY.resolve) # type: ignore
        listener = MainListener(devices)
        app.add_listener(listener) # type: ignore

        # Prometheus metrics, reachable from the cluster.
        async def handle_root(request: web.Request) -> web.Response:
            return web.Response(text='<a href="/metrics">Metrics</a>', content_type='text/html')

        metrics_app = web.Application()
        metrics_app.router.add_get('/', handle_root)
        metrics_app.router.add_get('/metrics', server_stats)

        metrics_runner = web.AppRunner(metrics_app, access_log=None)
        await metrics_runner.setup()
        await web.TCPSite(metrics_runner, '0.0.0.0', metrics_port).start()
        logging.info(f'Metrics server listening on 0.0.0.0:{metrics_port}')

        # Admin API for re-pairing. Bound to loopback on purpose: it is reached
        # only by `kubectl exec`ing into this container, never from the network.
        async def handle_devices(request: web.Request) -> web.Response:
            return web.json_response({'devices': listener.device_status()})

        async def handle_permit(request: web.Request) -> web.Response:
            try:
                seconds = int(request.query.get('seconds', 240))
            except ValueError:
                return web.json_response({'error': 'seconds must be an integer'}, status=400)
            seconds = max(1, min(seconds, 254)) # radio limit
            logging.info(f'Permit join requested via admin API for {seconds}s')
            await app.permit(seconds) # type: ignore
            return web.json_response({'status': 'ok', 'permit_seconds': seconds})

        admin_app = web.Application()
        admin_app.router.add_get('/devices', handle_devices)
        admin_app.router.add_route('*', '/permit', handle_permit)

        admin_runner = web.AppRunner(admin_app, access_log=None)
        await admin_runner.setup()
        await web.TCPSite(admin_runner, '127.0.0.1', admin_port).start()
        logging.info(f'Admin API listening on 127.0.0.1:{admin_port}')

        await asyncio.get_running_loop().create_future()
    except:
        traceback.print_exc()
        logging.info('Shutting down app...')
        if app: await app.shutdown()
        logging.info('Exiting.')
        os._exit(1) # This seems to be the only way to kill this f*$1ng Python process with asyncio...

if __name__ == '__main__':
    asyncio.run(main())
