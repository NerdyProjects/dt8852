# Copyright (C) 2020 - 2021 Randy Simons and contributers
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

import datetime
import time
from enum import Enum

import serial


class Dt8852:
    class Time_weighting(Enum):
        FAST = "Fast"
        SLOW = "Slow"

    class Frequency_weighting(Enum):
        DBA = "dB(A)"
        DBC = "dB(C)"

    class Range_threshold(Enum):
        UNDER = "Under range"
        OK = "Within range"
        OVER = "Over range"

    class Hold_mode(Enum):
        LIVE = "Live"
        MIN = "Minimum hold"
        MAX = "Maximum hold"

    class Range_mode(Enum):
        R_30_80 = "30dB - 80dB"
        R_50_100 = "50dB - 100dB"
        R_80_130 = "80dB - 130dB"
        R_30_130_AUTO = "30dB - 130dB auto range"

    class Recording_mode(Enum):
        NOT_RECORDING = "Not recording"
        RECORDING = "Recording"

    class Memory_store(Enum):
        AVAILABLE = "Storage available"
        FULL = "Storage full"

    class Battery_state(Enum):
        OK = "Battery OK"
        LOW = "Battery low"

    class Output_to(Enum):
        DISPLAY = "Digits"
        BAR_GRAPH = "Bar graph"

    class Command_token(Enum):
        POWER_DOWN = b'\x33'
        TOGGLE_RECORDING_MODE = b'\x55'
        TOGGLE_HOLD_MODE = b'\x11'
        TOGGLE_TIME_WEIGHTING = b'\x77'
        TOGGLE_RANGE_MODE = b'\x88'
        TOGGLE_FREQUENCY_WEIGHTING = b'\x99'
        GET_RECORDING = b'\xac'

    current_spl = None
    current_time = None
    time_weighting = None
    frequency_weighting = None
    range_threshold = None
    hold_mode = None
    range_mode = None
    recording_mode = None
    memory_store = None
    battery_state = None
    output_to = None

    __set_modes = []
    __set_mode_command = None
    __wait_for_value = None

    def __init__(self, serial: serial.Serial):
        self.serial = serial
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

    def __str__(self):
        return f"""current_time = {time.strftime("%X", self.current_time) if self.current_time else "Unknown"}
current_spl = {self.current_spl if self.current_spl else "Unknown" }dB
frequency_weighting = {self.frequency_weighting.value  if self.frequency_weighting else "Unknown"}
time_weighting = {self.time_weighting.value if self.time_weighting else "Unknown"}
range_threshold = {self.range_threshold.value if self.range_threshold else "Unknown"}
hold_mode = {self.hold_mode.value if self.hold_mode else "Unknown"}
range_mode = {self.range_mode.value if self.range_mode else "Unknown"}
recording_mode = {self.recording_mode.value if self.recording_mode else "Unknown"}
memory_store = {self.memory_store.value if self.memory_store else "Unknown"}
battery_state = {self.battery_state.value if self.battery_state else "Unknown"}
output_to = {self.output_to.value if self.output_to else "Unknown"}
serial = {self.serial.port if self.serial else "Unknown"}"""

    def set_mode(self, modes):
        """Sets the list of device configuration modes.

        Requested configuration is send to the device while calling
        decode_next_token.
        """
        self.__set_modes = modes
        self.__set_next_mode(first=True)

    def __set_next_mode(self, first=False):
        if not first:
            del self.__set_modes[0]

        if not len(self.__set_modes):
            self.__set_mode_command = None
            return

        mode = self.__set_modes[0]

        self.__wait_for_value = mode

        if mode.__class__ == Dt8852.Time_weighting:
            self.__set_mode_command = Dt8852.Command_token.TOGGLE_TIME_WEIGHTING
        elif mode.__class__ == Dt8852.Frequency_weighting:
            self.__set_mode_command = Dt8852.Command_token.TOGGLE_FREQUENCY_WEIGHTING
        elif mode.__class__ == Dt8852.Range_mode:
            self.__set_mode_command = Dt8852.Command_token.TOGGLE_RANGE_MODE
        elif mode.__class__ == Dt8852.Hold_mode:
            self.__set_mode_command = Dt8852.Command_token.TOGGLE_HOLD_MODE
        elif mode.__class__ == Dt8852.Recording_mode:
            self.__set_mode_command = Dt8852.Command_token.TOGGLE_RECORDING_MODE
        else:
            raise RuntimeError(
                f'Invalid mode "{mode}" of type "{mode.__class__.__name__}" provided.')

    def decode_next_token(self, changes_only=True):
        """Generator function. Waits for and decodes the next token from the device, yields the received
        token type and value.

        In addition, it sends commands to the device to achieve the requested modes specified by set_mode.

        Return value is a tuple containing decoded token type as string, its enumeration, and its value.
        If changes_only is True, decode_next_token returns only if the value is different than previously
        received value. If changes_only is False, all updates from device are returned,
        which is quite spammy.
        """

        supported_tokens = [ '02', '03', '04', '05', '06', '07', '08', '09', '0a', '0b', '0c', '0d', '0e', '0f', '11', '19', '1a', '1b', '1c', '1f', '30', '40', '4b', '4c' ]

        set_mode_throttle_counter = 0
        while True:
            # Wait for token start byte
            while self.serial.read() != b'\xa5':
                pass

            token = self.serial.read().hex()
            while token not in supported_tokens:
                token = self.serial.read().hex()

            # Get handler for the received token, and call it.
            decoded_token = getattr(self, f"_Dt8852__decode_token_0x{token}")()

            # Handle device configuration if requested via set_mode()
            if self.__set_mode_command is not None:
                set_mode_throttle_counter += 1

                # If the decoded_token shows the requested mode has reached the requested value,
                # continue with the next requested mode.
                # Otherwise, send the command for the requested mode change.
                if decoded_token[1].__class__ == self.__wait_for_value.__class__:
                    if decoded_token[1] == self.__wait_for_value:
                        self.__set_next_mode()
                else:
                    # The device is a bit deaf, or timing sensitive.
                    # Keep sending the appropriate command, until the requested state is reached.

                    # Don't spam device, otherwise the mode might "overshoot" its target.
                    # Devices sends 8 blocks of:
                    # part 1: range_mode, hold_mode, range_threshold,
                    # part 2: current_spl, output_to, frequency_weighting, current_time
                    # followed by 1 block of:
                    # part 1: memory_store, time_weighting, battery_state, recording_mode,
                    # part 2: same as above.
                    # So blocks are either 7 or 8 fields long.
                    # The correct timing to send a command, if such timing exists, is currently
                    # unknown. So, send the command at most once per block, i.e. 8+1
                    if set_mode_throttle_counter % 9 == 0:
                        self.serial.write(self.__set_mode_command.value)
                        self.serial.flush()

            if decoded_token[2] or not changes_only:
                yield decoded_token

    def __decode_token_0x02(self):
        # Time weighting Fast
        value_changed = self.time_weighting != Dt8852.Time_weighting.FAST
        self.time_weighting = Dt8852.Time_weighting.FAST
        return ("time_weighting", self.time_weighting, value_changed)

    def __decode_token_0x03(self):
        # Time weighting Slow
        value_changed = self.time_weighting != Dt8852.Time_weighting.SLOW
        self.time_weighting = Dt8852.Time_weighting.SLOW
        return ("time_weighting", self.time_weighting, value_changed)

    def __decode_token_0x04(self):
        # Max hold mode
        value_changed = self.hold_mode != Dt8852.Hold_mode.MAX
        self.hold_mode = Dt8852.Hold_mode.MAX
        return ("hold_mode", self.hold_mode, value_changed)

    def __decode_token_0x05(self):
        # Min hold mode
        value_changed = self.hold_mode != Dt8852.Hold_mode.MIN
        self.hold_mode = Dt8852.Hold_mode.MIN
        return ("hold_mode", self.hold_mode, value_changed)

    def __decode_token_0x06(self):
        # Current time in BCD; bit 5 of byte 0: 0 = AM, 1 = PM
        data = self.serial.read(3)

        # Convert data to time string…
        time_string = "{0:02x}:{1:02x}:{2:02x} {3}".format(data[0] & 0b_0001_1111, data[1], data[2], "pm" if data[0] >> 5 else "am")

        # …and parse time string to time object
        current_time = time.strptime(time_string, "%I:%M:%S %p")

        value_changed = self.current_time != current_time
        self.current_time = current_time
        return ("current_time", self.current_time, value_changed)

    def __decode_token_0x07(self):
        # Current measurement is over measurement range high threshold
        value_changed = self.range_threshold != Dt8852.Range_threshold.OVER
        self.range_threshold = Dt8852.Range_threshold.OVER
        return ("range_threshold", self.range_threshold, value_changed)

    def __decode_token_0x08(self):
        # Current measurement is under measurement range low threshold
        value_changed = self.range_threshold != Dt8852.Range_threshold.UNDER
        self.range_threshold = Dt8852.Range_threshold.UNDER
        return ("range_threshold", self.range_threshold, value_changed)

    def __decode_token_0x09(self):
        # Memory store is full
        value_changed = self.memory_store != Dt8852.Memory_store.FULL
        self.memory_store = Dt8852.Memory_store.FULL
        return ("memory_store", self.memory_store, value_changed)

    def __decode_token_0x0a(self):
        # Device is currently recording to memory
        value_changed = self.recording_mode != Dt8852.Recording_mode.RECORDING
        self.recording_mode = Dt8852.Recording_mode.RECORDING
        return ("recording_mode", self.recording_mode, value_changed)

    def __decode_token_0x0b(self):
        # Last measurement sent with 0x0d was shown on display readout
        value_changed = self.output_to != Dt8852.Output_to.DISPLAY
        self.output_to = Dt8852.Output_to.DISPLAY
        return ("output_to", self.output_to, value_changed)

    def __decode_token_0x0c(self):
        # Last measurement sent with 0x0d was shown in bargraph on display
        value_changed = self.output_to != Dt8852.Output_to.BAR_GRAPH
        self.output_to = Dt8852.Output_to.BAR_GRAPH
        return ("output_to", self.output_to, value_changed)

    def __decode_token_0x0d(self):
        # Current measurement, multiplied by 10, in BCD
        data = self.serial.read(2)
        splBcd = "{0:x}{1:02x}".format(data[0], data[1])
        current_spl = int(splBcd) / 10
        value_changed = self.current_spl != current_spl
        self.current_spl = current_spl
        return ("current_spl", self.current_spl, value_changed)

    def __decode_token_0x0e(self):
        # Live measurements mode (not max/min hold)
        value_changed = self.hold_mode != Dt8852.Hold_mode.LIVE
        self.hold_mode = Dt8852.Hold_mode.LIVE
        return ("hold_mode", self.hold_mode, value_changed)

    def __decode_token_0x0f(self):
        # Battery is low
        value_changed = self.battery_state != Dt8852.Battery_state.LOW
        self.battery_state = Dt8852.Battery_state.LOW
        return ("battery_state", self.battery_state, value_changed)

    def __decode_token_0x11(self):
        # Current measurement is within the current measurement range
        value_changed = self.range_threshold != Dt8852.Range_threshold.OK
        self.range_threshold = Dt8852.Range_threshold.OK
        return ("range_threshold", self.range_threshold, value_changed)

    def __decode_token_0x19(self):
        # Memory store is not full
        value_changed = self.memory_store != Dt8852.Memory_store.AVAILABLE
        self.memory_store = Dt8852.Memory_store.AVAILABLE
        return ("memory_store", self.memory_store, value_changed)

    def __decode_token_0x1a(self):
        # Device is not recording to memory
        value_changed = self.recording_mode != Dt8852.Recording_mode.NOT_RECORDING
        self.recording_mode = Dt8852.Recording_mode.NOT_RECORDING
        return ("recording_mode", self.recording_mode, value_changed)

    def __decode_token_0x1b(self):
        # Frequency weighting dBA
        value_changed = self.frequency_weighting != Dt8852.Frequency_weighting.DBA
        self.frequency_weighting = Dt8852.Frequency_weighting.DBA
        return ("frequency_weighting", self.frequency_weighting, value_changed)

    def __decode_token_0x1c(self):
        # Frequency weighting dBC
        value_changed = self.frequency_weighting != Dt8852.Frequency_weighting.DBC
        self.frequency_weighting = Dt8852.Frequency_weighting.DBC
        return ("frequency_weighting", self.frequency_weighting, value_changed)

    def __decode_token_0x1f(self):
        # Battery is OK
        value_changed = self.battery_state != Dt8852.Battery_state.OK
        self.battery_state = Dt8852.Battery_state.OK
        return ("battery_state", self.battery_state, value_changed)

    def __decode_token_0x30(self):
        # Measurement range 30-80 dB
        value_changed = self.range_mode != Dt8852.Range_mode.R_30_80
        self.range_mode = Dt8852.Range_mode.R_30_80
        return ("range_mode", self.range_mode, value_changed)

    def __decode_token_0x40(self):
        # Measurement range 30-130 dB (auto)
        value_changed = self.range_mode != Dt8852.Range_mode.R_30_130_AUTO
        self.range_mode = Dt8852.Range_mode.R_30_130_AUTO
        return ("range_mode", self.range_mode, value_changed)

    def __decode_token_0x4b(self):
        # Measurement range 50-100 dB
        value_changed = self.range_mode != Dt8852.Range_mode.R_50_100
        self.range_mode = Dt8852.Range_mode.R_50_100
        return ("range_mode", self.range_mode, value_changed)

    def __decode_token_0x4c(self):
        # Measurement range 80-130 dB
        value_changed = self.range_mode != Dt8852.Range_mode.R_80_130
        self.range_mode = Dt8852.Range_mode.R_80_130
        return ("range_mode", self.range_mode, value_changed)

    def get_recordings(self):
        """Generator function yielding all recorded sessions and data.

        For example, if there are two recorded sessions, this iterator yields:

        data_length <bytes to read>
        recording_start <frequency weighting, start time, sample interval, bytes read so far>
        <spl, timestamp, bytes read so far>
        <spl, timestamp, bytes read so far>
        …
        recording_complete <bytes read so far>
        recording_start <frequency weighting, start time, sample interval, bytes read so far>
        <spl, timestamp, bytes read so far>
        <spl, timestamp, bytes read so far>
        …
        recording_complete <bytes read so far>
        dump_complete <bytes read so far>

        Keep sending command until start byte"""
        while self.serial.read() != b'\xbb':
            self.serial.write(Dt8852.Command_token.GET_RECORDING.value)

        data_length = int.from_bytes(self.serial.read(2), byteorder='big')
        # correction
        data_length -= 100

        data_read = 0
        yield ("data_length", data_length, data_read)

        # Ignore the rest if there's no data anyway
        if data_length == 0:
            return

        token = self.serial.read()
        data_read += 1
        while True:
            if token != b'\xaa' and token != b'\xcc' and token != b'\xdd':
                yield("aborted_unexpected_data", token)
                return

            if token == b'\xdd':
                break

            # Get metadata
            metadata = self.serial.read(7)
            data_read += 7

            # Read timestamp of this batch from metadata…
            time_string = "20{0:02x}-{1:02x}-{2:02x} {3:02x}:{4:02x}:{5:02x} {6}".format(metadata[0], metadata[1], metadata[2], metadata[3] & 0b_0001_1111, metadata[4], metadata[5], "pm" if metadata[3] >> 5 else "am")

            # …and parse time string to time object
            start_time = datetime.datetime.strptime(time_string, "%Y-%m-%d %I:%M:%S %p")

            # get sample interval from metadata
            time_delta = datetime.timedelta(seconds=int(metadata[6]))

            yield("recording_start", Dt8852.Frequency_weighting.DBA if token == b'\xaa' else Dt8852.Frequency_weighting.DBC, start_time, time_delta, data_read)

            start_byte = self.serial.read()
            data_read += 1
            if start_byte != b'\xac':
                yield("aborted_unexpected_data", start_byte)
                return

            sample_time = start_time

            while True:
                token_or_spl_data = self.serial.read()
                data_read += 1
                # token_or_spl_data is a token iff value is higher than a BCD byte
                if token_or_spl_data > b'\x99':
                    token = token_or_spl_data
                    break
                # else it is data.
                else:
                    spl_data_2 = self.serial.read()
                    data_read += 1

                    # work around protocol bug, last sample is messed up, second byte is the 0xdd token..
                    if spl_data_2 == b'\xdd':
                        token = spl_data_2
                        break

                    # combine the two received BCD bytes
                    splBcd = "{0:x}{1:02x}".format(token_or_spl_data[0], spl_data_2[0])
                    spl = int(splBcd) / 10
                    yield("sample", spl, sample_time, data_read)
                    sample_time += time_delta

            yield("recording_complete",  data_read)

        yield("dump_complete",  data_read)
