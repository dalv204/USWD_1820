import time
import numpy as np
from datetime import datetime
import math
import time
# import connect_python
# import nominal as nm
from colorama import Fore, Style
import matplotlib.pyplot as plt

import serial
import struct

from scipy import signal
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter, medfilt

ser = serial.Serial('COM3', 921600, timeout=1)
time.sleep(.5)


START_byte1 = b'\xaa'
START_byte2 = b'\xab'
END_byte1 = b'\x00'
SAMPLE_RATE = 20000
BUF_LEN = 1024 # 1024 pairs

packet_size = 1+1 + (BUF_LEN*2)+ 1+1 # header + ID + data + end + checksum
last_block_id=None



# HARDWARE PARAMS

SENSOR_DIST = (6.6*25.4)/1000 # meters 

# filter definitions for improving hardware signal
fs = SAMPLE_RATE
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



# logger = connect_python.get_logger(__name__)



# def voltage_extractor(adc_signal):
#     """ does the opposite of to_255; takes a signal from esp32 and makes it a legible voltage value"""
#     vref = 3.3 # volts
#     return (adc_signal/4095) *vref # 12 bit resolution


def read_packet(duration_sec):
    """
    Makes sure packet is synchronized, well-formed, and not corrupt
    then returns this packet's data for processing.
    """
    last_block_id=None
    N = math.ceil(SAMPLE_RATE*duration_sec/BUF_LEN)*BUF_LEN

    piezo1_total = np.empty(N,dtype=np.uint8)
    piezo2_total = np.empty(N,dtype=np.uint8)
    idx=0

    total_samples = SAMPLE_RATE * duration_sec *2
    all_data= 0
    print(f"Recording for {duration_sec} seconds")

    while all_data < total_samples:
        
        b = ser.read(1)
        # print("reading")
        # print(b)

        if b == START_byte1:
            # print("passed first check")
            # print("passed second check")
            packet = ser.read(packet_size-1)

            if len(packet) <(packet_size-1):
                continue
            
            block_id = packet[0]
            raw_data = packet[1:-2] # exclude block ID, endbyte, and checksum
            received_checksum = packet[-1]

            # verify checksum
            calc_check = 0
            for b in packet[1:-1]:
                calc_check ^= b
            if calc_check!=received_checksum:
                print(f"CHECKSUM MISMATCH! BLOCK ID {block_id}")
                continue

            if last_block_id is not None:
                diff = (block_id-last_block_id)%256
                if diff>1:
                    # we must have dropped a number!!
                    print(f"Dropped {diff-1} blocks!")
                last_block_id = block_id
            

            # fast conversion and bit masking 4-bit channel ID
            chunk = np.frombuffer(raw_data, dtype=np.uint8).reshape(-1,2) # reshape 50,2
            piezo1 = chunk[:,0]
            piezo2 = chunk[:,1]

            piezo1_total[idx:idx+len(piezo1)] = piezo1
            piezo2_total[idx:idx+len(piezo2)] = piezo2
            idx+=len(piezo1)

            # print(len(piezo1))
            all_data += len(piezo1)*2
    
    return piezo1_total, piezo2_total



a_data, b_data = read_packet(3)
# print(f"here is a_data: {a_data}")
# print(f"here is b_data: {b_data}")

np.save('dual_test_a.npy', a_data)
np.save('dual_test_b.npy', b_data)
ser.close()
print("serial should be closed!")


time.sleep(.01)

a_data = np.load('dual_test_a.npy')
b_data = np.load('dual_test_b.npy')

# print(f"here is a_data: {a_data}")
# print(f"here is b_data: {b_data}")


# trying a filter ###########################

# fs = SAMPLE_RATE
time = np.linspace(0, len(a_data)/fs, num=len(b_data))

# window_size = 500

# moving_avg = np.convolve(data, np.ones(window_size)/window_size, mode='same')
# filtered_data = signal.filtfilt(b,a,data)
# ########################################### ^^^ didn't work well so not currently in use

def align_signals(p1, p2, sampling_rate = SAMPLE_RATE, conv_delay = 2.5e-6):
    """ aligns the signals given a 2.5 microsecond conversion delay """
    ts = 1.0 / sampling_rate # gives us the sampling interval
    # find the shift factor we need
    alpha = conv_delay / ts 

    # basic linear interpolation to "guess" where the signal was
    p2_aligned = np.zeros_like(p2)
    # we need to start with the first one because we depend on prev samples
    p2_aligned[1:] = (1-alpha) * p2[1:] + alpha*p2[:-1]

    # handle first sample, which we'll just copy
    p2_aligned[0] = p2[0]

    # maybe we should consider sinc sampling later if 
    # we want to end up with a more precise result - 
        # essentially we upsample our data, shift it, then down sample again 
        # to put it in position well.
    return p1, p2_aligned


def peak_localization(filt_sig):
    """ return location of peaks given filtered signal """
    segment_length = SAMPLE_RATE # samples per length

    peaks = np.array([np.max(np.abs(filt_sig[i:i+segment_length])) for i 
                    in range(0,len(filt_sig),segment_length)])
    
    print(peaks)

    max_peak = np.max(peaks)
    max_peak_locations = np.where(np.abs(filt_sig)>=max_peak)
    avg_peak = np.average(peaks)
    print(f"average peak is {avg_peak}")
    general_peak_locations = np.where(filt_sig>avg_peak)
    if len(general_peak_locations[0])==0 and avg_peak!=0:
        print("SHOULD BE HERE")
        print(np.where(np.abs(filt_sig)>=avg_peak-5))
        return np.where(np.abs(filt_sig)>=avg_peak)[0]
    general_peak_values = np.array([filt_sig[i] for i in general_peak_locations[0]])

    true_peak_locations,_ = signal.find_peaks(np.abs(general_peak_values), height=0,distance=1)

    # print(f"these are the max peaks: {max_peak_locations}")
    # print(f" at values {[filt_sig[i] for i in max_peak_locations]}")
    # print(f"there are {len(true_peak_locations)} peaks calculated")

    # return [general_peak_locations[0][i] for i in true_peak_locations]
    # return max_peak_locations[0]
    return general_peak_locations[0]

# def peak_localization(filt_sig):
    energy = onset_energy(filt_sig)

    thresh = np.mean(energy) + 6*np.std(energy)
    idx = np.where(energy > thresh)[0]

    return idx

def detect_edge_time(sig, fs):
    """ detects strong edge """
    sig = sig-np.mean(sig)
    #grab me some derivatives!
    d = np.gradient(sig)
    idx = np.argmin(d)
    return idx

def onset_energy(sig):
    sig = sig - np.mean(sig)
    d = np.abs(np.gradient(sig))
    return gaussian_filter1d(d, sigma=2)

# code for correlation!



def calculate_localization(sig_a, sig_b, fs = SAMPLE_RATE, v_wood=5000):  #v_wood based on trials
    """ 
    uses input from both signals to calculate the time difference and thus return localization (1D) 

    sig_a is coming from the left (should mark)
    sig_b is coming from the right 
    fs is sampling freq
    v-wood is the sound in the wood (m/s) - we should calibrate this
    """

    max_distance_cm = 14 # cm
    fs = fs*5 # try upsampling to reduce sensitivity

    # 1 pre-processing: remove DC offset and any fuzz that we can
    # data = savgol_filter(data-np.mean(data), window_length=50, polyorder=3)

    sig_a_smooth = sig_a# gaussian_filter1d(sig_a-np.mean(sig_a),sigma=2)
    sig_b_smooth = sig_b#gaussian_filter1d(sig_b-np.mean(sig_b),sigma=2)

    indices_a = peak_localization(sig_a_smooth)
    indices_b = peak_localization(sig_b_smooth)

    # just get distance from one to the other
    print(f"{indices_a=}")
    print(f"{indices_b=}")


    
    if indices_a is None or len(indices_a)==0:
        # no tap detected?
        return None,None
    start_idx_a = float('inf')#max(0, indices_a[0]-100) # include some pre-trigger
    start_idx_b = max(0, indices_b[0]-50)
    print(f"start_idx {start_idx_a=}")
    print(f"start_idxb {start_idx_b=}")


    start_idx = min(start_idx_a, start_idx_b)
    if start_idx==start_idx_a:
        # then we want to use b as the end
        end_idx = min(len(sig_a_smooth), start_idx_a+100+50) # +100 adds what we subtracted earlier, leaving it the original-20

    else:
        # use a as the end
        end_idx = min(len(sig_a_smooth), start_idx_b+100+50)

    # now we want ot get the windows
    a_win = gaussian_filter1d(sig_a_smooth[start_idx:end_idx], sigma=1)
    b_win = gaussian_filter1d(sig_b_smooth[start_idx:end_idx], sigma=1)

    # ta = detect_edge_time(a_win, fs)
    # tb = detect_edge_time(b_win, fs)
    # print(f"start index {start_idx}")
    # print(f"end index {end_idx}")

    print(f"a_win is of length {len(a_win)}")
    ea = onset_energy(a_win)
    eb = onset_energy(b_win)

    ea = ea / (np.max(ea) + 1e-9)
    eb = eb / (np.max(ea) + 1e-9)

    corr = signal.correlate(np.abs(a_win), np.abs(b_win), mode='full')

    peak_indices = signal.find_peaks(corr,distance=1)[0]
    if len(peak_indices)==0:
        # just grab from before
        peak_indices = [np.argmax(corr) - (len(ea)-1)]

    candidates=[]
    for idx in peak_indices:
        peak_pos = int(idx) 
        center = len(ea)-1
        lag = peak_pos-center
        # print(f"{center=}")
        # print(f"{peak_pos-center=}")
        # print(f"{peak_pos=}")
        dt = (lag/fs) - 2.5e-6 
        # print(f'{(lag/fs)}')
        
        d1 = ((dt*v_wood)/2.0) * 100
        print(f"distance is {d1}")
        print(f"idx is {idx}")
        print(f"center is {len(ea)-1}")

        candidates.append({
            'idx': idx,
            'amp': corr[idx],
            'd1':d1,
            'lag':lag,
            'dt':dt
        })

    valid_candidates = [c for c in candidates if abs(c['d1']) <=max_distance_cm*2]
    if valid_candidates:
        best_few = sorted(valid_candidates, key=lambda c: abs(c['amp']), reverse=True)
        print(f"{len(best_few)=}")
        print(f"{best_few[0]['idx']=}")

        total_amp = sum(abs(c['amp']) for c in best_few)
        weighted_d1 = sum(c['d1']*abs(c['amp']) / total_amp for c in best_few)
        best = {
            'd1': weighted_d1,
            'amp': total_amp/len(best_few),
            'idx':best_few[0]['idx'], # jsut for reference really
            'dt':best_few[0]['dt'] # could also compute weighted time
        }
        reason = 'valid'

        # if len(best_few)>1:
            
        #     best = best_few[1] # grab the second one? never seems to be the biggest one?
        # else:
        #     best = best_few[0]
        # reason = 'valid'
    else:
        best = min(candidates, key=lambda c: c['d1'])
        reason = 'clamped'

    

    d1 = best['d1']
    constrained_d1 = min(max_distance_cm, max(-max_distance_cm, d1)) #np.clip(d1, -max_distance_cm, max_distance_cm)
    print(f"chosen peak idx = {best['idx']},dt = {best['dt']}, amp = {best['amp']}, d1 = {best['d1']}cm ({reason})")



    plt.plot(list(range(len(a_win))), a_win)
    plt.plot(list(range(len(a_win))), b_win)
    plt.show()


    # # print(f"len sig_a {len(sig_a)}")
    # # print(f"len sig_b {len(sig_b)}")

    # # print(len(a_win))
    # # print(len(b_win))
    # # 2 do cross correlation (extract initial time stamp (or just always send with the same start!))
    # a_der = np.abs(np.gradient(a_win))
    # b_der = np.abs(np.gradient(b_win))

    # # in 'full' mode will return array of length len(a) + len(b) - 1
    # corr = signal.correlate(a_der, b_der, mode='full')

    # # 3 find the peak, 'zero lag' is at the center of full correlation array 
    #     #   (do we want the peak, or the tiny drop before it?)
    
    # center = len(a_win) -1 
    # k_int = np.argmax(np.abs(corr))
    # print(f"k_int location is {k_int}")

    # 5 convert the peak index into a time delay between both signals
        #   make the distance relative to the center of the wood piece

    # peak_time_offset = k_int - center
    # sample_diff = int(ta-tb)
    # dt = (sample_diff/fs) - 2.5e-6 
    print(f"dt is {dt:.15f}")
    # print(f"ta-tb/fs is {sample_diff/fs:.15f}")
    # print(f"sample difference is {sample_diff:.15f}")
    # d1 = ((SENSOR_DIST - dt*v_wood)/2.0)*100 # distance to sensor on right (cm)
    # d1 = ((dt*v_wood)/2.0)*100 # distance to sensor on right (cm)



    return constrained_d1+12, corr

    # 6 now convert to distance from 


# calc = calculate_localization(data, data)
# print(f"distance is {calc[0]} cm")





# doing a moving average makes us unable to see scratches

# plot
# a_data, b_data = align_signals(a_data,b_data)

def apply_notch(data, notch_freq=60.0, quality_factor=30.0, fs=SAMPLE_RATE):
    # Design the notch filter
    b, a = signal.iirnotch(notch_freq, quality_factor, fs)
    # Apply it
    filtered_data = signal.filtfilt(b, a, data)
    return filtered_data


a_data= a_data-np.mean(a_data)# gaussian_filter1d(sig_a-np.mean(sig_a),sigma=2)
b_data= b_data-np.mean(b_data)
a_data = apply_notch(a_data)
b_data = apply_notch(b_data)
a_data = apply_notch(a_data, notch_freq=58)
b_data = apply_notch(b_data, notch_freq=58)
a_data = medfilt(a_data, kernel_size=3)
b_data = medfilt(b_data, kernel_size=3)

a_data, b_data = align_signals(a_data, b_data)


# a_data = gaussian_filter1d(a_data,sigma=1.5, order=1)
# b_data = gaussian_filter1d(b_data,sigma=1.5, order=1)



# def remove_glitches(data, max_diff=50)

print(peak_localization(a_data))
local_data, corr = calculate_localization(a_data,b_data)
print(f"about {local_data}cm from center")
plt.plot(list(range(len(corr))), corr, label="correlation")
plt.show()
plt.plot(time,a_data, label = 'a_data')
plt.plot(time,b_data, label = 'b_data')

plt.legend()
plt.xlabel('Time [s]')
plt.ylabel('Amplitude')
plt.title('a_data and b_data')


# plt.plot(time, filtered_data)
# plt.plot(time, data-moving_avg)
plt.show()