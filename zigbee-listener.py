#!/usr/bin/env python3

import asyncio
from bellows.zigbee.application import ControllerApplication


class MainListener:
    '''
    Contains callbacks that zigpy will call whenever something happens.
    Look for `listener_event` in the Zigpy source or just look at the logged warnings.
    '''
    def device_joined(self, device):
        print(f'device_joined: {device}')

    def device_initialized(self, device):
        print(f'device_initialized {device}')

async def main():
    app = await ControllerApplication.new(config={
        'database_path': 'zigbee.db',
        'device': {
            'path': '/dev/ttyUSB0',
        }
    }, auto_form=True)
    
    listener = MainListener()
    app.add_listener(listener)

    print('Listening...')
    await asyncio.get_running_loop().create_future()

if __name__ == '__main__':
    asyncio.run(main())
