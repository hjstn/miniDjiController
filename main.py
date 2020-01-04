# Known working pings
# 55 0d 04 33 0a 0e 02 00 40 06 27 84 05
# 55 0d 04 33 0a 0e 03 00 40 06 01 f4 4a
# 55 0d 04 33 0a 0e 04 00 40 06 27 1c 3e
# 55 0d 04 33 0a 0e 05 00 40 06 01 6c 71
import serial, pyvjoy, argparse

parser = argparse.ArgumentParser(description='Mavic Mini RC <-> VJoy interface.')

parser.add_argument('-p', '--port', help='RC Serial Port', required=True)
parser.add_argument('-d', '--device', help='VJoy Device ID', type=int, default=1)
parser.add_argument('-i', '--invert', help='Invert lv, lh, rv, rh, or cam axis', nargs='*', default=['lv', 'rv'])

args = parser.parse_args()

invert = frozenset(args.invert)

# Maximum value for VJoy to handle (0x8000)
maxValue = 32768

# Reverse-engineered. Seems any one of the known working pings are okay.
pingData = bytearray.fromhex('550d04330a0e0300400601f44a')

# Open serial.
try:
    s = serial.Serial(port=args.port, baudrate=115200)
    print('Opened serial device:', s.name)
except serial.SerialException as e:
    print('Could not open serial device:', e)
    exit(1)

# Open VJoy device.
try:
    j = pyvjoy.VJoyDevice(args.device)
    print('Opened VJoy device:', j.rID)
except pyvjoy.exceptions.vJoyException as e:
    print('Could not open VJoy device:', e)
    exit(1)

# Stylistic: Newline for spacing.
print('\nPress Ctrl+C (or interrupt) to stop.\n')

# Process input (min 364, center 1024, max 1684) -> (min 0, center 16384, max 32768)
def parseInput(input, name):
    output = (int.from_bytes(input, byteorder='little') - 364) * 4096 // 165

    # Invert axes (Windows detected lv and rv as inverted originally)
    if name in invert:
        output = maxValue - output

    return output

try:
    while True:
        # Ping device (to get new data).
        s.write(pingData)

        # Don't write to a new line every time.
        print('\rPinged. ', end='')

        data = s.readline()

        # Reverse-engineered. Controller input seems to always be len 38.
        if len(data) == 38:
            # Reverse-engineered. Whole section done from MITM'ing DJI Flight Simulator.
            left_vertical = parseInput(data[13:15], 'lv')
            left_horizontal = parseInput(data[16:18], 'lh')

            right_vertical = parseInput(data[10:12], 'rv')
            right_horizontal = parseInput(data[7:9], 'rh')

            camera = parseInput(data[19:21], 'cam')

            # TODO: Implement buttons (couldn't find while reverse-engineering).

            # Update VJoy input.
            j.data.wAxisX = left_horizontal
            j.data.wAxisY = left_vertical
            j.data.wAxisXRot = right_horizontal
            j.data.wAxisYRot = right_vertical
            j.data.wSlider = camera

            # Send VJoy input update.
            j.update()

            # Log to console.
            print('L: H{0:06d},V{1:06d}; R: H{2:06d},V{3:06d}, CAM: {4:06d}'.format(left_horizontal, left_vertical, right_horizontal, right_vertical, camera), end='')
except serial.SerialException as e:
    # Stylistic: Newline to stop data update and spacing.
    print('\n\nCould not read/write:', e)
except KeyboardInterrupt:
    # Stylistic: Newline to stop data update and spacing.
    print('\n\nDetected keyboard interrupt.')

    pass

print('Stopping.')