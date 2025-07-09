# CANBell - Bell sensor
#
# Copyright (C) 2024  Alan Sparrow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import asyncio.stream
import json
import time

import machine

from .mcp2515 import MCP2515
from .mcp2515.canio import Message
from . import msgid

BELLS = "x1234567890ET"

# Accept all messages
MASKS = [0x0, 0x0]
FILTERS = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0]


class Delays:
    def __init__(self):
        self.set([])

    def load(self, filename="delays.json"):
        with open(filename) as f:
            self.delays = json.load(f)
            self.nbells = len(self.delays)

    def save(self, filename="delays.json"):
        with open(filename, "w") as f:
            json.dump(self.delays, f)

    def set(self, delays):
        self.delays = delays
        self.nbells = len(delays)


# Output the bell message at specified time
async def strike(bell, strike_ticks_ms, log_stream):
    t = time.ticks_diff(strike_ticks_ms, time.ticks_ms())
    await asyncio.sleep_ms(t)

    print(BELLS[bell], end="")

    log_stream.write(b"B,")
    log_stream.write(b",".join([str(bell).encode(), str(strike_ticks_ms).encode()]))
    log_stream.write(b"\n")
    await log_stream.drain()


async def can_listen(can, uart_stream, delays):
    nbells = delays.nbells

    # Listen for bell messages
    listener = can.listen()
    while True:
        if listener.in_waiting():
            rx_msg = listener.receive()

            bell = rx_msg.id & ~msgid.CMD_MASK
            if bell > 0 and bell <= nbells:
                strike_ticks_ms = time.ticks_add(
                    time.ticks_ms(), delays.delays[bell - 1]
                )
                asyncio.create_task(strike(bell, strike_ticks_ms, uart_stream))

        await asyncio.sleep_ms(0)


async def uart_listen(uart_stream, delays):
    while True:
        rxd = await uart_stream.readline()
        data = rxd.split(b",")

        if data[0].strip() == b"G":
            # Return delays
            uart_stream.write(b"D,")
            uart_stream.write(b",".join([str(d).encode() for d in delays.delays]))
            uart_stream.write(b"\n")
            await uart_stream.drain()

        elif data[0] == b"D":
            # Set delays
            dlys = [int(d) for d in data[1:]]
            if len(dlys) == delays.nbells:
                delays.set(dlys)
                delays.save()


async def can_loopback(can):
    while 1:
        for bell in [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6]:
            msg = Message(bell, data=b"")

            try:
                can.send(msg)
            except RuntimeError:
                print("Can't send ding message")

            await asyncio.sleep_ms(300)

        await asyncio.sleep_ms(300)


async def sensor_loopback(can):
    msg = Message(msgid.ECHO_REQ, data=b"")
    while 1:
        try:
            can.send(msg)
        except RuntimeError:
            print("Can't send echo_req message")

        await asyncio.sleep_ms(1000)


async def main():
    # Create CAN driver
    spi = machine.SPI(0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
    cs = machine.Pin(9, machine.Pin.OUT, value=1)

    can = MCP2515(spi, cs)
    can.load_filters(MASKS, FILTERS)

    uart = machine.UART(0, 115200)
    uart_stream = asyncio.stream.Stream(uart)

    delays = Delays()
    delays.load()

    await asyncio.gather(
        can_listen(can, uart_stream, delays), uart_listen(uart_stream, delays)
    )


async def test():
    # Create CAN driver (in loopback mode)
    spi = machine.SPI(0, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
    cs = machine.Pin(9, machine.Pin.OUT, value=1)

    # can = MCP2515(spi, cs, loopback=True, silent=True)
    can = MCP2515(spi, cs)
    can.load_filters(MASKS, FILTERS)

    uart = machine.UART(0, 115200)
    uart_stream = asyncio.stream.Stream(uart)

    delays = Delays()
    delays.load()

    await asyncio.gather(
        # can_loopback(can),
        sensor_loopback(can),
        can_listen(can, uart_stream, delays),
        uart_listen(uart_stream, delays),
    )
