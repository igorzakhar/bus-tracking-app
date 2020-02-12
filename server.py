import functools
import json
import logging
import sys

import trio
from trio_websocket import serve_websocket, ConnectionClosed


async def receive_bus_coordinates(request, send_channel):
    buses = {}

    ws = await request.accept()

    while True:

        try:
            received_message = await ws.get_message()
            bus_info = json.loads(received_message)

            logging.debug(f'Received message: {bus_info}')

            buses.update({bus_info['busId']: bus_info})

            await send_channel.send(buses)

        except ConnectionClosed:
            break


async def talk_to_browser(request, receive_channel):
    ws = await request.accept()

    async for buses_info in receive_channel:
        buses = [bus_info for bus_info in buses_info.values()]

        browser_msg = {
            'msgType': 'Buses',
            'buses': buses
        }
        try:
            await ws.send_message(json.dumps(browser_msg, ensure_ascii=True))
            logging.debug(f'Talk to browser: {browser_msg["buses"]}')

            await trio.sleep(0.01)

        except ConnectionClosed:
            break


async def main():
    logging.getLogger('trio-websocket').setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    send_channel, receive_channel = trio.open_memory_channel(0)

    receive_coordinates = functools.partial(
        receive_bus_coordinates,
        send_channel=send_channel
    )

    handle_connection_browser = functools.partial(
        talk_to_browser,
        receive_channel=receive_channel
    )

    ssl_context = None
    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            serve_websocket,
            receive_coordinates,
            '127.0.0.1',
            8080,
            ssl_context
        )
        nursery.start_soon(
            serve_websocket,
            handle_connection_browser,
            '127.0.0.1',
            8000,
            ssl_context
        )


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        sys.exit()
