import json
import logging
from itertools import cycle, chain

import trio
from trio_websocket import serve_websocket, ConnectionClosed


async def load_bus_route(filename):
    async with await trio.open_file(filename) as fp:
        return await fp.read()


async def run_bus(request):
    ws = await request.accept()

    bus_route = json.loads(await load_bus_route('routes/156.json'))

    coordinates = bus_route['coordinates']
    route_cycle = cycle(chain(coordinates, coordinates[::-1]))

    while True:
        try:

            bus_coords = next(route_cycle)
            lat, lng = bus_coords[0], bus_coords[1]
            server_msg = {
                "msgType": "Buses",
                "buses": [
                    {
                        "busId": "1234567890",
                        "lat": lat,
                        "lng": lng,
                        "route": bus_route["name"]
                    },
                ]
            }

            await ws.send_message(json.dumps(server_msg))
            logging.debug(server_msg['buses'])

            await trio.sleep(0.5)

        except ConnectionClosed:
            break


async def main():
    logging.getLogger('trio-websocket').setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    await serve_websocket(run_bus, '127.0.0.1', 8000, ssl_context=None)


trio.run(main)
