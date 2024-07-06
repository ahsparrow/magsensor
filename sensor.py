import asyncio
from machine import SPI, Pin, unique_id
from mcp2515 import MCP2515 as CAN
from mcp2515.canio import Message
from primitives import RingbufQueue
import struct
import time

# Discard everything except ID=0
MASKS = [0x7FF, 0x7FF]
FILTERS = [0, 0, 0, 0, 0, 0]

DEFAULT_CAN_ID = 0x7FF

SCK_PIN = 2
MOSI_PIN = 3
MISO_PIN = 4
CAN_CS_PIN = 9
LED_PIN = 18
SENSOR_PIN = 21


async def can_task(msg_q, can_id, board_id):
    spi = SPI(0, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
    cs = Pin(CAN_CS_PIN, Pin.OUT, value=1)

    can = CAN(spi, cs)
    can.load_filters(MASKS, FILTERS)

    # Ding message is "D" + two bytes delay + 5 bytes id
    ding_buf = bytearray(board_id)
    ding_buf[0] = ord("D")

    listener = can.listen()
    while True:
        # Check for outgoing requests
        if not msg_q.empty():
            delay = await msg_q.get()
            struct.pack_into("<H", ding_buf, 1, min(delay, 65535))

            msg = Message(id=can_id, data=ding_buf)
            can.send(msg)

            print("Ding", delay)

        # Process any incoming messages
        if listener.in_waiting():
            rx_msg = listener.receive()

            if len(rx_msg.data) > 0:
                # Echo
                if chr(rx_msg.data[0]) == "E":
                    # Echo message is "e" + 7 bytes id
                    buf = bytearray(board_id)
                    buf[0] = ord("e")
                    msg = Message(id=can_id, data=buf)

                    can.send(msg)

                # CAN id set
                elif (
                    chr(rx_msg.data[0]) == "I"
                    and len(rx_msg.data) == 8
                    and rx_msg.data[2:] == board_id[2:]
                ):
                    can_id = rx_msg.data[1]

                    # ACK message is "i" + 7 bytes id
                    buf = bytearray(board_id)
                    buf[0] = ord("i")
                    msg = Message(id=can_id, data=buf)

                    can.send(msg)

                    # Store id
                    with open("_can_id.txt", "w") as f:
                        f.write(f"{can_id}\n")

        await asyncio.sleep_ms(0)


# Send message after specified delay
async def trigger_task(msg_q, delay_ms):
    await asyncio.sleep_ms(delay_ms)
    await msg_q.put(delay_ms)


# Monitor magnetic sensor
async def sensor_task(msg_q):
    pin = Pin(SENSOR_PIN, Pin.IN)
    led = Pin(LED_PIN, Pin.OUT, value=0)

    trigger_delay = 0

    while 1:
        # Wait for sensor active
        while pin.value() == 1:
            await asyncio.sleep_ms(0)

        start = time.ticks_us()
        led.value(1)

        # Start trigger messaging task
        asyncio.create_task(trigger_task(msg_q, trigger_delay))

        # Wait 10ms after sensor last active for "debounce""
        timeout = 0
        while timeout < 10000:
            if pin.value() == 0:
                stop = time.ticks_us()
                timeout = 0
            else:
                timeout = time.ticks_diff(time.ticks_us(), stop)

            await asyncio.sleep_ms(0)

        led.value(0)

        # Calculate delay from sensor start to centre
        trigger_delay = int(time.ticks_diff(stop, start) / 2000)
        trigger_delay = max(trigger_delay, 100)

        await asyncio.sleep_ms(100)


async def main(can_id=None):
    # If CAN id not specified read value from file
    if can_id is None:
        try:
            with open("_can_id.txt") as f:
                can_id = int(f.readline())
                if can_id < 1 or can_id > 0x7FF:
                    can_id = DEFAULT_CAN_ID
                    print("CAN id out of range, using default")

        except (OSError, ValueError):
            can_id = DEFAULT_CAN_ID
            print("Can't read CAN id, using default")

    q = RingbufQueue(5)
    await asyncio.gather(can_task(q, can_id, unique_id()), sensor_task(q))


if __name__ == "__main__":
    asyncio.run(main())
