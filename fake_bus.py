import json
from itertools import cycle, chain
import logging
import os
import random
import sys

import trio
from trio_websocket import open_websocket_url, ConnectionClosed


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def run_bus(ws, bus_id, route):
    route_coords = route['coordinates']

    start_offset = random.randrange(len(route_coords))
    route_offset = chain(route_coords[start_offset:], route_coords[::-1])

    route_loop = cycle(
        chain(route_offset, route_coords[:-(len(route_coords)-start_offset)])
    )

    while True:
        try:
            bus_coords = next(route_loop)
            lat, lng = bus_coords[0], bus_coords[1]
            bus_info = {
                'busId': bus_id,
                'lat': lat,
                'lng': lng,
                'route': route['name']
            }

            message = json.dumps(bus_info, ensure_ascii=True)
            await ws.send_message(message)

            logging.debug(f'Sent message: {bus_info}')

            await trio.sleep(1)

        except ConnectionClosed as err:
            logging.exception(err, exc_info=False)
            break


async def main():
    logging.getLogger('trio-websocket').setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    buses_per_route = 2

    try:
        async with open_websocket_url('ws://127.0.0.1:8080') as ws:
            async with trio.open_nursery() as nursery:

                for route in load_routes():
                    for bus_index in range(buses_per_route):
                        bus_id = generate_bus_id(route['name'], bus_index)
                        nursery.start_soon(run_bus, ws, bus_id, route)

    except OSError as ose:
        logging.exception('Connection attempt failed: %s', ose)
        raise


if __name__ == '__main__':
    try:
        trio.run(main)
    except (KeyboardInterrupt, OSError, trio.MultiError):
        sys.exit()
