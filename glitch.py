import subprocess
import pigpio
import time


pi = pigio.pi()

G1 = 4  # airtag power
G2 = 24  # glitch pin
G3 = 3  # airtag boot feedback pin
G4 = 30  # random pin

pi.set_mode(G1, pigpio.OUTPUT)
pi.set_mode(G2, pigpio.OUTPUT)

def glitch(delay, pulse_length, prev_callback):

    if prev_callback:
        prev_callback.cancel()

    # when airtag comes on, send glitch pulse with length pulse_length after a delay of delay
    pi.write(G2, 1)
    glitch_wave = []

    glitch_wave.append(pigpio.pulse(1<<G2, 1<<G4, delay))
    glitch_wave.append(pigpio.pulse(1<<G4, 1<<G2, pulse_length))
    glitch_wave.append(pigpio.pulse(1<<G2, 1<<G4, delay))

    pi.wave_clear()
    pi.wave_add_generic(glitch_wave)
    glitch_wave_id = pi.wave_create()

    def send_glitch_pulse(*args):
        pi.wave_send_once(glitch_wave_id)
        while pi.wave_tx_busy(): # wait for waveform to be sent
           time.sleep(0.1)
        pi.write(G2, 1)

    send_glitch_pulse_callback = pi.callback(G3, pigpio.FALLING_EDGE, send_glitch_pulse)

    # power cycle
    pi.write(G1, 0)
    time.sleep(0.05)
    pi.write(G1, 1)

    return send_glitch_pulse_callback


def try_dump_image():
    try:
        subprocess.check_output([
            'openocd',
            '-f', 'interface/raspberrypi2-native.cfg',
            '-c', 'transport select swd',
            '-f', 'testnrf.cfg',
            '-c', 'init; dump_image nrf52_dumped2.bin 0x0 0x1000; exit'
        ], stderr=subprocess.STDOUT)
        return True
    except:
        return False


def run():
    for delay in range(200, 4000):
        callback = None
        for pulse_length in range(1, 10):
            callback = glitch(delay, pulse_length, callback)
            for _ in range(5):
                if try_dump_image():
                    print(f"successfully dumped image with delay {delay} and pulse_length {pulse_length}")
                    sys.exit(0)

run()
