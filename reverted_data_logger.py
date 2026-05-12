import time
import numpy as np
from datetime import datetime
import time
# import connect_python
# import nominal as nm
from colorama import Fore, Style
import matplotlib.pyplot as plt

import serial
import struct

from scipy import signal
import math

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
import pyqtgraph as pg


################## ATTENTION #####################
# THIS IS THE REVERTED FILE FOR JUST GATHERING 
#        SIMPLE DATA FROM A SINGLE PIEZO
###################################################



# get the correct structure down!
# start byte: 0x7E
# end byte: 0x7F
START_byte1 = b'\xcd'
START_byte2 = b'\xab'
I2S_SAMPLE_RATE = 40000
# END = 0x7F
# MAX_LEN = 256

# filter definitions for improving hardware signal
fs = I2S_SAMPLE_RATE
low = 70
high = 19000
# b,a = signal.butter(4, Wn=[low, high], btype='bandpass', fs=fs, output='ba')
b,a = signal.iirnotch(60.0, 30.0, fs)


# # a few command types that we can use
# ADC_STREAMING = 0x01
# STOP_STREAMING = 0x02
# WAVE_GEN = 0x03


# ADC_CHANNELS = ["ADC0", "ADC1", "ADC2"] # for labeling if I feel like it 

# # Define colors using colorama
GREEN = Fore.GREEN + Style.DIM
RED = Fore.RED + Style.BRIGHT
RESET = Style.RESET_ALL

ser = serial.Serial('COM3', 921600, timeout=1)
time.sleep(.5)
BUF_LEN = 1024
packet_size = BUF_LEN * 2 # 2 bytes per sample

# logger = connect_python.get_logger(__name__)



def voltage_extractor(adc_signal):
    """ does the opposite of to_255; takes a signal from esp32 and makes it legible voltage value"""
    vref = 3.3 # volts
    return (adc_signal/4095) *vref # 12 bit resolution


def read_packet_total(duration_sec):
    """
    Makes sure packet is synchronized, well-formed, and not corrupt
    then returns this packet's data for processing.
    """

    total_samples = I2S_SAMPLE_RATE * duration_sec
    N = math.ceil(I2S_SAMPLE_RATE*duration_sec/BUF_LEN)*BUF_LEN
    all_data = np.empty(N, dtype=np.uint16)
    idx=0
    print(f"Recording for {duration_sec} seconds")

    while idx < total_samples:
        
        b = ser.read(1)
        # print("reading")
        # print(b)

        if b == START_byte1:
            # print("passed first check")
            if ser.read(1)==START_byte2:
                # print("passed second check")
                raw_payload = ser.read(packet_size)

                # fast conversion and bit masking 4-bit channel ID
                chunk = np.frombuffer(raw_payload, dtype=np.uint16) & 0x0FFF
                all_data[idx:idx+len(chunk)] = chunk
                idx+=len(chunk)
    
    return all_data

def read_packet_chunk():
    """ should we just design this to be a 'forever reader' ? """
    while True:
        b = ser.read(1)
        if b == START_byte1:
            if ser.read(1)==START_byte2:
                raw_payload = ser.read(packet_size)
                chunk = np.frombuffer(raw_payload, dtype=np.uint16) & 0x0FFF
                return chunk
            


def apply_notch(data, notch_freq=60.0, quality_factor=30.0, fs=I2S_SAMPLE_RATE):
    # Design the notch filter
    b, a = signal.iirnotch(notch_freq, quality_factor, fs)
    # Apply it
    filtered_data = signal.filtfilt(b, a, data)
    return filtered_data

plt.ion()

live_graph_duration = 5 # seconds
N = math.ceil(I2S_SAMPLE_RATE*live_graph_duration/BUF_LEN)*BUF_LEN
buffer = np.empty(N, dtype=np.float32)  # why are we making everything a float 32? that makes no sense...


app = QApplication([])
win = pg.GraphicsLayoutWidget(show = True, title="Live piezo trace")
win.resize(900,400)

plot = win.addPlot(title="live signal")
plot.setLabel("bottom", "Time", units="s")
plot.setLabel("left", "Amplitude")
plot.setYRange(-500,1000)
curve = plot.plot(pen=pg.mkPen("y", width=1))

x = np.linspace(-live_graph_duration, 0, N, dtype=np.float32)


def update():

    # this updates the live graph, but we still want to be able to view 
    # the data after we put it here, and we want to be able to run an fft
    # then detect different kinds of taps
    global buffer 
    chunk = read_packet_chunk().astype(np.float32)
    chunk -=np.mean(chunk)
    buffer = np.roll(buffer, -len(chunk))
    buffer[-len(chunk):] = chunk
    filtered = apply_notch(apply_notch(buffer),58)
    


    # now actually plot the data
    curve.setData(x,buffer)



timer = QTimer()
timer.timeout.connect(update)
timer.start(20) # updates every 20 ms
QApplication.instance().exec_()



data = read_packet_total(5)
data = data-np.mean(data) # subtracting the offset should make the math cleaner?
np.save('swipe.npy', data)
ser.close()



print("serial should be closed!")


time.sleep(.01)

data = np.load('mary_2.npy')

fs = I2S_SAMPLE_RATE
time = np.linspace(0, len(data)/fs, num=len(data))

window_size = 500

moving_avg = np.convolve(data, np.ones(window_size)/window_size, mode='same')
# filtered_data = signal.filtfilt(b,a,data)
data = apply_notch(data)
data = apply_notch(data, 58)

energy = data**2 # see different ways to quickly find the data
smooth = np.convolve(
    energy,np.ones(200)/200,
    mode='same'
)

peaks, props = signal.find_peaks(
    smooth,
    height=np.average(smooth),
    distance = 0.06 * I2S_SAMPLE_RATE # give it 0.06 seconds per knock
)

print(f"{peaks=}")
print(f"{len(peaks)=}")

plt.plot(time,smooth)
plt.show()

# doing a moving average makes us unable to see scratches

# plot
plt.plot(time,data)
# plt.plot(time, filtered_data)
# plt.plot(time, data-moving_avg)
plt.show()