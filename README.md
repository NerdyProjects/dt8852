# dt8852 overview

dt8852 is a cross-platform Python package and module for reading and controlling CEM DT-8852 and equivalent Sound Level Meter and Data Logger devices.

* Project homepage: https://codeberg.org/randysimons/dt8852
* Download: https://pypi.org/project/dt8852/
* License: GPLv3 or later

# Features

* Read current SPL value as measured from device.
* Read current device configuration.
* Configure the device.
* Download recorded sessions directly to .csv.
* Can be used directly from command line interface, and in your own application using the API.
* Single dependency: [pySerial](https://github.com/pyserial/pyserial).

# Compatible devices

* [CEM DT-8852](http://www.cem-instruments.com/en/Product/detail/id/1294) (OEM)

This device is also re-branded and sold as:

* Trotec SL-400
* Voltcraft SL-451
* ATP SL-8852
* … probably various others.

The CEM DT-8851 lacks the data logger functionality, but might otherwise be supported as well. However, due to availability of only a Trotec SL-400, the package is only tested on this device.

# Installation

Install the package using PIP:

```
$ pip install dt8852
```

Or directly from source:

```
$ pip install git+https://codeberg.org/randysimons/dt8852.git#egg=dt8852
```

On Debian / Ubuntu, use `pip3` instead of `pip`.

## Device driver installation

The devices internally uses a USB-to-UART bridge by Silicon Labs. Your OS needs a driver for this to work, so the device can be accessed as a regular RS232 serial (COM) device.

* On **Linux**, the driver is already available on many distributions. No action is needed.
* On **Windows 10**, the device is automatically recognized, and Windows installs the appropriate driver. No action is needed. Alternatively, if you already have installed the provided software, no action is needed. If needed, the USB driver is available directly from [Silicon Labs](https://www.silabs.com/products/development-tools/software/usb-to-uart-bridge-vcp-drivers).
* On **Mac OSX**, a USB driver is available from [Silicon Labs](https://www.silabs.com/products/development-tools/software/usb-to-uart-bridge-vcp-drivers).

# Usage

After installation, the module can be run directly from the command line, and can be used as module in your own Python application (see below). In both cases, the basic setup applies:

1. Connect the device to computer by USB.
2. Switch on the device.
3. Press button "Setup" once, to enable data communication mode.

## Command line interface

`python -m dt8852 MODE`, where `MODE` is one of:

* `live` get live SPL measurements from device, output to stdout.
* `set_mode` configure device according to specified values and exits.
* `get_mode` retrieve current device configuration and exit.
* `download` to download recorded sessions as command separated value (csv) files and exit.

Use `python -m dt8852 -h` for basic help, or `python -m dt8852 MODE -h` for mode-specific help, for example `python -m dt8852 live -h`.

Note: by default the serial interface used is `COM3` on Windows, `/dev/ttyUSB0` on other OSses. You can override this by using the `--serial_port` argument. The currently available serial interfaces can be found by running `python -m  serial.tools.list_ports` on the command line.

### Examples

Note: these example assume Python version 3 (i.e. python3) is the default interpreter.

#### Basic live output

```
$ python -m dt8852 live
33.3
32.4
32.9
71.8
```

#### Verbose level 1 live output

```
$ python -m dt8852 live -v
2020-10-01 22:27:02.806050,37.3
2020-10-01 22:27:03.304626,33.0
2020-10-01 22:27:03.802777,56.2
2020-10-01 22:27:04.301302,53.0
```
Tip: if you redirect the output to a file, e.g. `python -m dt8852 live -v > output.csv`, you can easily import the output in a spreadsheet.

#### Verbose level 5 live output

```
$ python -m dt8852 live -vvvvv
('frequency_weighting', <Frequency_weighting.DBA: 'dB(A)'>, True)
('current_time', time.struct_time(tm_year=1900, tm_mon=1, tm_mday=1, tm_hour=22, tm_min=29, tm_sec=4, tm_wday=0, tm_yday=1, tm_isdst=-1), True)
('range_mode', <Range_mode.R_30_80: '30dB - 80dB'>, True)
('hold_mode', <Hold_mode.LIVE: 'Live'>, True)
('range_threshold', <Range_threshold.OK: 'Within range'>, True)
('current_spl', 41.9, True)
('output_to', <Output_to.BAR_GRAPH: 'Bar graph'>, True)
```

#### Get current configuration

```
$ python -m dt8852 get_mode
current_time = 22:31:39
current_spl = 40.7dB
frequency_weighting = dB(A)
time_weighting = Fast
range_threshold = Within range
hold_mode = Live
range_mode = 30dB - 80dB
recording_mode = Not recording
memory_store = Storage available
battery_state = Battery OK
output_to = Digits
serial = /dev/ttyUSB0
```

#### Set configuration

Sets modes Range 30dB - 80dB, dB(C), slow, and start recording to internal storage.

```
$ python -m dt8852 set_mode --range R_30_80 --freqweighting DBC --timeweighting SLOW --record
```

#### Stop recording

```
$ python -m dt8852 set_mode --record NOT_RECORDING
```

#### Download recordings

**Note:** make sure the device is not recording anymore before downloading, otherwise memory corruption will occur.

```
$ python -m dt8852 download
Downloading 2349 bytes
Writing file: Recording 2020-10-01 21-49-19, dB(A), sample interval 1s.csv
Number of recorded samples written to file: 7
Writing file: Recording 2020-10-01 21-49-30, dB(A), sample interval 1s.csv
Number of recorded samples written to file: 6
Writing file: Recording 2020-10-01 21-50-57, dB(A), sample interval 1s.csv
Number of recorded samples written to file: 1148
All done
```
## API

The module can be used in your own applications as well. To use, instantiate an object of class **`dt8852.Dt8852`**. See below for examples.

### Class methods

**`__init__(serial: serial.Serial)`** Instantiates a new Dt8852 handler on provided serial interface.

**`__str__()`** Returns string representation, with all currently known device values.

**`decode_next_token(changes_only=True)`** Generator function. Waits for and decodes the next token from the device, yields the received token type and value.

In addition, it sends commands to the device to achieve the requested modes specified by `set_mode()`.

Return value is a tuple containing decoded token type as string, its enumeration, and its value.
If changes_only is True, decode_next_token returns only if the value is different than previously received value. If changes_only is False, all updates from device are returned,
which is quite spammy.

**`set_mode(modes)`** Sets the list of device configuration modes. Modes is a mutable sequence containing the requested device configuration. This list can contain any of `Dt8852.Time_weighting.FAST`, `Dt8852.Time_weighting.SLOW`, `Dt8852.Frequency_weighting.DBA`, `Dt8852.Frequency_weighting.DBC`, `Dt8852.Hold_mode.LIVE`, `Dt8852.Hold_mode.MIN`, `Dt8852.Hold_mode.MAX`, `Dt8852.Range_mode.R_30_80`, `Dt8852.Range_mode.R_50_100`, `Dt8852.Range_mode.R_80_130`, `Dt8852.Range_mode.R_30_130_AUTO`, `Dt8852.Recording_mode.NOT_RECORDING`, `Dt8852.Recording_mode.RECORDING`.

Requested configuration is send to the device while calling decode_next_token. The process is done, if the passed modes sequence is empty.

Currently the correct mechanism of precisely when to send the commands to the device is not well understood. More often than not, the device ignores the send commands. The current implementation tries to mitigate this by periodically sending the command, and then waits if it has the desired effect. This method is not perfect, resulting in incorrect device configuration. Of course, you can always use the device's own buttons to set the desired mode at any time.

**`get_recordings()`**  Generator function yielding all recorded sessions and data.

For example, if there are two recorded sessions, this iterator yields:

```
data_length [bytes to read]
recording_start [frequency weighting, start time, sample interval, bytes read so far]
[spl, timestamp, bytes read so far]
[spl, timestamp, bytes read so far]
…
recording_complete [bytes read so far]
recording_start [frequency weighting, start time, sample interval, bytes read so far]
[spl, timestamp, bytes read so far]
[spl, timestamp, bytes read so far]
…
recording_complete [bytes read so far]
dump_complete [bytes read so far]
```

### Instance variables

The devices simply outputs a stream of current values. The `decode_next_token()`-loop decodes this stream, and gradually fills the following instance variables. These are read-only.

**`current_spl`** Most recent SPL measurement.

**`current_time`** Current time on device.

**`time_weighting`** `Dt8852.Time_weighting.FAST`, `Dt8852.Time_weighting.SLOW` or `None` if not yet known.

**`frequency_weighting`** `Dt8852.Frequency_weighting.DBA`, `Dt8852.Frequency_weighting.DBC` or `None` if not yet known.

**`range_threshold`** `Dt8852.Range_threshold.UNDER`, `Dt8852.Range_threshold.OK`, `Dt8852.Range_threshold.OVER` or `None` if not yet known.

**`hold_mode`** `Dt8852.Hold_mode.LIVE`, `Dt8852.Hold_mode.MIN`, `Dt8852.Hold_mode.MAX` or `None` if not yet known.

**`range_mode`** `Dt8852.Range_mode.R_30_80`, `Dt8852.Range_mode.R_50_100`, `Dt8852.Range_mode.R_80_130`, `Dt8852.Range_mode.R_30_130_AUTO` or `None` if not yet known.

**`recording_mode`** `Dt8852.Recording_mode.NOT_RECORDING`, `Dt8852.Recording_mode.RECORDING` or `None` if not yet known.

**`memory_store`** `Dt8852.Memory_store.AVAILABLE`, `Dt8852.Memory_store.FULL` or `None` if not yet known.

**`battery_state`** `Dt8852.Battery_state.OK`, `Dt8852.Battery_state.LOW` or `None` if not yet known.

**`output_to`** `Dt8852.Output_to.DISPLAY`, `Dt8852.Output_to.BAR_GRAPH` or `None` if not yet known. This indicates whether the last reported SPL-update was shown on the digits display, or the bar graph display on device.

### Examples

Minimalistic example, which decodes and prints all updates coming from the device connected on serial port `/dev/ttyUSB0`:
```python
import serial, dt8852

spl_meter = dt8852.Dt8852(serial.Serial('/dev/ttyUSB0'))
for data in spl_meter.decode_next_token():
    print(data)
```

A more extended example of API usage is available on https://codeberg.org/randysimons/dt8852.

# Attribution

The project is based on information from the [Sigrok device wiki for CEM DT-8852](https://sigrok.org/wiki/CEM_DT-8852).