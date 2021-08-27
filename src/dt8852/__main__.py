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

from .dt8852 import Dt8852
from platform import system
import argparse, datetime, serial

# Handle command line interface.

def __get_modes_from_args():
    set_modes = []

    # set modes based on arguments passed
    for modes, argument in [(Dt8852.Range_mode, args.range), (Dt8852.Frequency_weighting, args.freqweighting), (Dt8852.Time_weighting, args.timeweighting), (Dt8852.Hold_mode, args.hold), (Dt8852.Recording_mode, args.record)]:
        for mode in modes:
            if mode.name == argument:
                set_modes.append(mode)
                break

    return set_modes

def run_get_mode(dt8852, args):
    # Loop until all modes have set.
    for _ in dt8852.decode_next_token():
        if None not in [dt8852.current_spl, dt8852.current_time, dt8852.time_weighting, dt8852.frequency_weighting, dt8852.range_threshold, dt8852.hold_mode, dt8852.range_mode, dt8852.recording_mode, dt8852.memory_store, dt8852.battery_state, dt8852.output_to]:
            break

    print(dt8852)

def run_set_mode(dt8852, args):
    set_modes = __get_modes_from_args()

    dt8852.set_mode(set_modes)

    # Wait until all modes have set.
    for _ in dt8852.decode_next_token():
        if len(set_modes) == 0:
            break

    print(dt8852)

def run_live(dt8852, args):
    dt8852.set_mode(__get_modes_from_args())

    if args.verbosity <= 1:
        # In verbose level 0, print SPL on display only
        # In verbose level 1, print SPL on display and current time
        for data in dt8852.decode_next_token():
            if (data[1] == Dt8852.Output_to.DISPLAY):
                if args.verbosity == 0:
                    print(dt8852.current_spl)
                else:
                    print(f"{datetime.datetime.now()!s},{dt8852.current_spl}")
    elif args.verbosity <= 3:
        # In verbose level 2, print SPL on display and bar graph only
        # In verbose level 3, print SPL on display and bar graph, and current time
        for data in dt8852.decode_next_token():
            if (data[0] == 'current_spl'):
                if args.verbosity == 2:
                    print(data[1])
                else:
                    print(f"{datetime.datetime.now()!s},{data[1]}")
    else:
        # In verbose level 4, print only changed values, reducing the output.
        # In verbose level 5, print all values.
        for data in dt8852.decode_next_token(args.verbosity == 4):
            print(data)

def run_download(dt8852, arg):
    import csv
    last_progress = 0

    # Must get iterator from iterable, because of the nested looping of the iterator.
    iter = dt8852.get_recordings().__iter__()

    for data in iter:
        if data[0] == "data_length":
            data_length = data[1]
            print(f"Downloading {data_length} bytes")
        elif data[0] == "recording_start":
            filename = f'Recording {data[2].strftime("%Y-%m-%d %H-%M-%S")}, {data[1].value}, sample interval {data[3].seconds}s.csv'
            print(f"Writing file: {filename}")
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", data[1].value])
                num_samples_in_recording = 0
                for sample in iter:
                    if sample[0] == "recording_complete":
                        print(f"Number of recorded samples written to file: {num_samples_in_recording}")
                        break
                    writer.writerow([sample[2].isoformat(), sample[1]])
                    num_samples_in_recording += 1
                    progress = 100 * sample[3] // data_length
                    if progress != last_progress:
                        print(f"Progress: {progress}%", end="\r")
                        last_progress = progress
        elif data[0] == "dump_complete":
            break
    print("All done")

parser = argparse.ArgumentParser(prog=f'python -m dt8852', description='A Python package for controlling and reading CEM DT-8852 Sound Pressure Level Meter and Data Logger. Also known as Trotec SL-400, Voltcraft SL-451, ATP SL-8852. To use, connect a supported SPL meter via the USB-port. Switch on the device. Press Setup to enable the serial interface. Run %(prog)s MODE, where MODE is one of the operation modes.')
parser.add_argument('--serial_port', help='Serial port to use. URL\'s are supported, e.g. rfc2217://remote.host.example:2000 (default: %(default)s)', default='COM3' if system() == 'Windows' else '/dev/ttyUSB0')

mode_parser = argparse.ArgumentParser(add_help=False)
mode_parser.add_argument('--range', choices=[i.name for i in list(Dt8852.Range_mode)], help="dB Range 30dB-80dB, 50dB-100dB, 80dB-130dB or 30dB-130dB auto mode")
mode_parser.add_argument('--freqweighting', choices=[i.name for i in list(Dt8852.Frequency_weighting)], help="A-weighting or C-weighting")
mode_parser.add_argument('--timeweighting', choices=[i.name for i in list(Dt8852.Time_weighting)], help="Fast or Slow measurements")
mode_parser.add_argument('--hold', choices=[i.name for i in list(Dt8852.Hold_mode)], help="Live, hold MIN or hold MAX")
mode_parser.add_argument('--record', choices=[i.name for i in list(Dt8852.Recording_mode)], help="Record to memory")

subparsers = parser.add_subparsers(title='Mode of operation', metavar="MODE", help='%(prog)s has two primary modes of operation. See %(prog)s %(metavar)s -h for details for each %(metavar)s.', required=True)
parser_live = subparsers.add_parser('live', help='Live output of realtime measured values and settings.  Note: setting mode is glitchy and might not work correctly.', parents=[mode_parser])
parser_set_mode = subparsers.add_parser('set_mode', help='Sets requested modes, then quits. Note: setting mode is glitchy and might not work correctly.', parents=[mode_parser])
parser_get_mode = subparsers.add_parser('get_mode', help='Prints current mode from device, then quits.')
parser_download = subparsers.add_parser('download', help='Download previously recorded data. Exports data as one csv file per session.')

parser_live.add_argument("-v", "--verbosity", action="count", default=0, help="Verbose level 0 (default): only SPL measurements from display. Vebose level 1 (-v): SPL and current time. Vebose level 2 (-vv): SPL on display and bar graph. Vebose level 3 (-vvv): SPL on display and bar graph, and current time. Verbose level 4 (-vvvv): all changed values. Verbose level 5 (-vvvvv): all output.")

parser_live.set_defaults(func=run_live)
parser_set_mode.set_defaults(func=run_set_mode)
parser_get_mode.set_defaults(func=run_get_mode)
parser_download.set_defaults(func=run_download)

args = parser.parse_args()

if args.func:
    with serial.serial_for_url(args.serial_port, 9600) as sp:
        dt8852 = Dt8852(sp)
        args.func(dt8852, args)
