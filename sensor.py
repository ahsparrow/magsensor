import asyncio
from machine import SPI, Pin
from mcp2515 import MCP2515 as CAN
from mcp2515.canio import Message
from primitives import RingbufQueue
import struct
import time

# Discard everything except ID=0
MASKS = [0x7FF, 0x7FF]
FILTERS = [0, 0, 0, 0, 0, 0]

CAN_ID = 1

SCK_PIN = 2
MOSI_PIN = 3
MISO_PIN = 4
CAN_CS_PIN = 9
LED_PIN = 18
SENSOR_PIN = 21


async def can_task(msg_q, id):
    spi = SPI(0, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
    cs = Pin(CAN_CS_PIN, Pin.OUT, value=1)

    can = CAN(spi, cs)
    can.load_filters(MASKS, FILTERS)

    listener = can.listen()
    while True:
        # Check for outgoing requests
        if not msg_q.empty():
            delay = await msg_q.get()
            print("Ding", delay)
            data = struct.pack("<cI", b"D", delay)

            tx_msg = Message(id=id, data=data)
            can.send(tx_msg)

        # Process any incoming messages
        if listener.in_waiting():
            rx_msg = listener.receive()

            if rx_msg.data == b"ECHO":
                tx_msg = Message(id=id, data=b"ECHO")
                can.send(tx_msg)

        await asyncio.sleep_ms(0)


async def trigger_task(msg_q, delay_ms):
    await asyncio.sleep_ms(delay_ms)
    await msg_q.put(delay_ms)


async def sensor_task(msg_q):
    pin = Pin(SENSOR_PIN, Pin.IN)
    led = Pin(LED_PIN, Pin.OUT, value=0)

    trigger_delay = 0

    while 1:
        # Wait for sensor active and record start time
        while pin.value() == 1:
            await asyncio.sleep_ms(0)

        led.value(1)

        # Start trigger message task
        start = time.ticks_us()
        asyncio.create_task(trigger_task(msg_q, trigger_delay))

        # Wait 10ms after sensor last active
        timeout = 0
        while timeout < 10000:
            if pin.value() == 0:
                stop = time.ticks_us()
                timeout = 0
            else:
                timeout = time.ticks_diff(time.ticks_us(), stop)

            await asyncio.sleep_ms(0)

        led.value(0)

        # Delay from sensor start to centre
        trigger_delay = int(time.ticks_diff(stop, start) / 2000)

        await asyncio.sleep_ms(1000)


async def main():
    q = RingbufQueue(5)
    await asyncio.gather(can_task(q, CAN_ID), sensor_task(q))


if __name__ == "__main__":
    asyncio.run(main())
