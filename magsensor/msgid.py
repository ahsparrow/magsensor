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

# Message ID is 7 bits command + 4 bits bell number

CMD_MASK = 0x7F0

# -----------------
# Sensor messages

# Bell passing bottom dead centre
BELL = 0x00

# Sensor acknowledge
ACK = 0x10

# -------------------
# Receiver messages

# Resquest all sensors to send ACK
ECHO_REQ = 0x80

# Request all sensors to send ACK instead of next ding
IDENT_REQ = 0x90

# Set bell number
BELL_SET = 0xA0
