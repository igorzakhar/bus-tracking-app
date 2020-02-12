import json
from itertools import cycle, chain
import logging
import os
import sys

import trio
from trio_websocket import open_websocket_url, ConnectionClosed


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


async def run_bus(ws, bus_id, route):
    coordinates = route['coordinates']
    route_cycle = cycle(chain(coordinates, coordinates[::-1]))

    while True:
        try:
            bus_coords = next(route_cycle)
            lat, lng = bus_coords[0], bus_coords[1]
            coordinates = {
                'busId': f'{route["name"]}-0',
                'lat': lat,
                'lng': lng,
                'route': route['name']
            }

            message = json.dumps(coordinates, ensure_ascii=True)
            await ws.send_message(message)

            logging.debug(f'Sent message: {coordinates}')

            await trio.sleep(1)

        except ConnectionClosed as err:
            logging.exception(err, exc_info=False)
            break


async def main():
    logging.getLogger('trio-websocket').setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    try:
        async with open_websocket_url('ws://127.0.0.1:8080') as ws:
            async with trio.open_nursery() as nursery:
                for route in load_routes():
                    bus_id = route['name']
                    nursery.start_soon(run_bus, ws, bus_id, route)
    except OSError as ose:
        logging.exception('Connection attempt failed: %s', ose)
        raise


if __name__ == '__main__':
    try:
        trio.run(main)
    except (KeyboardInterrupt, OSError, trio.MultiError):
        sys.exit()
