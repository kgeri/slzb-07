#!/usr/bin/env python3

from bellows.zigbee.application import ControllerApplication
import asyncio
import logging
import os
import time
import tomllib


async def main():
    # Logging config
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%dT%H:%M:%SZ')
    logging.Formatter.converter = time.gmtime

    # Config load
    with open('config.toml', 'rb') as f:
        config = tomllib.load(f)

    ezsp_device = config.get('ezsp_device', '/dev/ttyUSB0')

    # Radio init
    database_path = 'zigbee.db'
    auto_form = not os.path.isfile(database_path)
    logging.info(f'Listening on radio: {ezsp_device}, auto_form={auto_form}, allowing joins...')

    try:
        app = await ControllerApplication.new(config={
            'database_path': database_path,
            'device': {
                'path': ezsp_device,
            }
        }, auto_form=auto_form, start_radio=True)
        await app.permit(240)
        await asyncio.get_running_loop().create_future()
    finally:
        logging.info('Shutting down app and exiting...')
        await app.shutdown()

if __name__ == '__main__':
    asyncio.run(main())