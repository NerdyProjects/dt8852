from dt8852 import Dt8852
import serial
import time

# This will:
# * open a serial connection to the device,
# * configure the device for dB(C) measurements in 30dB - 80dB range, with slow metering,
# * start recording,
# * for 10 seconds, output the measured dB values to the console,
# * stop recording,
# * dumps all recordings to output.
#
# However, controlling recording from this API is not recommended, as it
# can result in data corruption in the device, making it impossible to
# download all sessions. The only remedy then is to clear the recorded data.

# For Windows, try COM3.
with serial.Serial('/dev/ttyUSB0') as sp:

    # Instantiate object
    dt8852 = Dt8852(sp)

    # Sets modes: range 30dB - 80dB, slow, dB(C) and start recording.
    modes = [Dt8852.Range_mode.R_30_80, Dt8852.Time_weighting.SLOW, Dt8852.Frequency_weighting.DBC, Dt8852.Recording_mode.RECORDING]
    dt8852.set_mode(modes)

    # Process incoming data from device until all modes have set.
    for _ in dt8852.decode_next_token():
        if len(modes) == 0:
            break

    # Record for about 10 seconds.
    end_time = time.time() + 10

    # Wait for and decode next token from device. By default, this only yields
    # if the value of the token changed, so value_changed will always be True
    # in this case.
    # Print the measured SPL (dB(C)) for 10 seconds, then continue.
    for (token_type, token_value, value_changed) in dt8852.decode_next_token():
        if (token_type == 'current_spl'):
            print(token_value)
        if time.time() >= end_time:
            break

    # Stop recording.
    modes = [Dt8852.Recording_mode.NOT_RECORDING]
    dt8852.set_mode(modes)
    for _ in dt8852.decode_next_token():
        if len(modes) == 0:
            break

    # Dump recordings to output
    for data in dt8852.get_recordings():
        print(data)
