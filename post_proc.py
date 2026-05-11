import numpy as np
from numpy.fft import fft, rfft
import math
import matplotlib.pyplot as plt
from scipy.signal import iirnotch, filtfilt, find_peaks, resample
from lib6003.audio import wav_play, wav_read, wav_write
from scipy.io.wavfile import read

threshold = 2200
succession_threshold = 170
window_size = 1000
window_shift = window_size //2 # IMPORTANT: increase shift if picking up too many peaks

################## RAW DATA ##################
hard_taps_arr = np.array(np.load("tests/hard_taps_noisy.npy"))
knocks_arr = np.load("tests/knocks_noisy.npy")
mary = np.load("raw_piezo_waveforms/mary.npy")
succession = np.load("raw_piezo_waveforms/dual_test_a.npy")

# samples = mary
# name = "mary"

samples = succession
name = "succession"

# samples = knocks_arr
# name = "knocks"

# print(samples.size)
fs = 40000 # Hz
T = 1.0/fs
N = len(samples) # num samples
t = np.linspace(0.0, N*T, N)

################## PIANO AUDIO ##################
c6, f1 = wav_read("piano_notes/c6.wav")
d6, f2 = wav_read("piano_notes/d6.wav")
e6, f3 = wav_read("piano_notes/e6.wav")
f6, f4 = wav_read("piano_notes/f6.wav")
g6, f5 = wav_read("piano_notes/g6.wav")

note_sig = d6
num_out_samples = len(note_sig) * fs // f1
d6_raw_resampled = resample(note_sig, num_out_samples)
resampled = d6_raw_resampled

resamp_min = np.min(resampled)
resamp_max = np.max(resampled)

rescaled = -1 + 2 * (resampled - resamp_min) / (resamp_max - resamp_min)
# print(rescaled[:20])
print(num_out_samples)

# print(f1, f2, f3, f4, f5)

tap_note_map = {1: c6, 2: d6, 3: e6, 4: f6, 5: g6}
##############################################



bw = 2 # bandwidth [Hz]
f0 = 60 # center freq [Hz]
# w0 = f0/(0.5 * fs)
Q = f0/bw # Quality factor
# Q = 20
# print(f'{w0=} {Q=}')
# b, a = iirnotch(w0, Q)
b, a = iirnotch(f0, Q, fs)
# b2, a2 = iirnotch(200, Q, fs)
filt_samples = filtfilt(b, a, samples)
# filt_samples = filtfilt(b2, a2, filt_samples)

# Notch bandstop filter for 60hz noise
for i in range(1,6):
    b, a = iirnotch(f0 + 120*i, Q, fs)
    filt_samples = filtfilt(b, a, filt_samples)

def apply_notch_filter_60hz(samples, f0=60, bw=2, fs=fs):
    Q = f0/bw # Quality factor
    b, a = iirnotch(f0, Q, fs)
    filt_samples = filtfilt(b, a, samples)

    # Notch bandstop filter for 60hz noise
    for i in range(1,6):
        b, a = iirnotch(f0 + 120*i, Q, fs)
        filt_samples = filtfilt(b, a, filt_samples)

    return filt_samples



################## WINDOWS ##################
last_idx = -1
windows = []
i = 0
peak_idxs = [] 
thresh = succession_threshold
while i < N:
    if filt_samples[i] > thresh: #using post notch filter!
        peak_idxs.append(int(i))
        buf = []
        last_idx = i
        for j in range(window_size):
            idx = i + j - window_size//3
            if idx >= 0 and idx < N: #out of bounds check
                buf.append(samples[idx])
        windows.append(buf)
        i += window_shift # may want to tune this window idx shift
    else:
        i += 1
        # windows.extend([0] * 10)
# out = windows.flatten()
    
################## IDENTIFY MULTI TAPS ##################
# making upper threshold for multi taps (up to 5 in a row)
one_sec = fs
thresh_time_diff_per_multitap = int(0.75*fs)
ts_tap = {} #keys are timestamps, values are number of taps
n = 0
# for n, peak_ts in enumerate(peak_idxs):\
while n < len(peak_idxs):
    for num_taps in range(4, 0, -1):
        # print(n)
        # print(num_taps)
        
        # if(peak_idxs[n]==307291 and num_taps ==2):
        #     print(num_taps, n, len(peak_idxs))
        matched = False
        if n + num_taps >= len(peak_idxs): # check "future" ts in bounds
            continue
        
        timestamp = peak_idxs[n]
        time_diff = peak_idxs[n+num_taps] - timestamp
        
        # if(timestamp==307291):
        #     print(num_taps, n, time_diff)
        if time_diff <= thresh_time_diff_per_multitap:    
            ts_tap[timestamp] = num_taps + 1
            n += num_taps + 1
            matched = True
            break
    if not matched: #singular peak
        ts_tap[peak_idxs[n]] = 1
        n += 1
        
     # check that the break actually breaks before this n increments
print(f'num peaks: {len(peak_idxs)}, {peak_idxs=}')   
print(f'{ts_tap=}')  

################## ASSIGN AUDIO BASED ON TAPS ##################
audio_out = np.zeros(N)
for timestamp, num_taps in ts_tap.items():
    note = tap_note_map[num_taps]
    end_timestamp = min(timestamp + len(note), N)
    # print(timestamp, end_timestamp)
    audio_out[timestamp: end_timestamp] = note[:end_timestamp - timestamp]

wav_write(audio_out, fs, f'audio_out/{name}_piano_out.wav')

################## FIND FREQ PEAKS OVER ALL WINDOWS ##################
peaks = []
def plot_freq_pk_all_windows(windows):
    for i, window in enumerate(windows):
        # peaks.append(find_peaks(window))
        # times = np.linspace(0.0, (len(window))*T, len(window))
        # plt.plot(times, window, label=f'window {i}')

        fft_out_windows = np.abs(rfft(window)) # Frequency Domain 
        freq_bins_windows = np.fft.rfftfreq(len(window), d=1/fs)
        # plt.vlines(freq_bins_windows, fft_out_windows)   
        plt.plot(freq_bins_windows, fft_out_windows)   
    # print (i)
    plt.xlim(90, 1000)                                 
    plt.xlabel("Frequency (Hz)")
    plt.ylim(0, 40000)                               
    plt.ylabel("Amplitude")
    plt.legend()
    plt.title(f'{name} window fft')
    plt.show()

# plot_freq_pk_all_windows(windows)

# print(peaks)

# Noise window
# windows = samples[:last_idx-10]

# t2 = np.linspace(0.0, (len(windows))*T, len(windows))

################## PLOT RAW WINDOW ##################
def plot_raw_sig_all_windows(windows):
    # for i, window in enumerate(windows):
    #     ts = np.linspace(0.0, (len(window))*T, len(window))
    #     plt.plot(ts, window, label=f'window {i}')
    subsamples = windows[0]
    t2 = np.linspace(0.0, (len(subsamples))*T, len(subsamples))

    # subsamples2 = windows[1]
    # t3 = np.linspace(0.0, (len(subsamples2))*T, len(subsamples2))
    plt.plot(t2, subsamples, label="window 0")  
    # plt.plot(t3, subsamples2, label="window 1")  
    # plt.plot   
    plt.xlabel("time(s)")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.title(f'{name} window')
    plt.show()

# plot_raw_sig_all_windows(windows)

################## PLOT WINDOW FFT ##################
# fft_out_windows = np.abs(rfft(windows)) # Frequency Domain 
# # print(fft_out_windows)
# freq_bins_windows = np.fft.rfftfreq(len(windows), d=1/fs)
# plt.plot(freq_bins_windows, fft_out_windows)    
# plt.xlim(90, 1000)                                 
# plt.xlabel("Frequency (Hz)")
# plt.ylim(0, 40000)                               
# plt.ylabel("Amplitude")
# plt.title(f'{name} window fft')
# plt.show()


######################################################


################## SAMPLES VS. TIME ##################
def plot_raw_samples(samples, ts=False, filter=True, label=name, fs=fs):
    T = 1.0/fs
    N = len(samples)
    if not ts:
        t = np.linspace(0.0, N*T, N)
    else: 
        t = np.linspace(0.0, N, N)
    if filter:
        samples = apply_notch_filter_60hz(samples)
    plt.plot(t, samples)    
    # plt.xlim(0, 300)                                 
    plt.xlabel("time (s)")
    # plt.ylim(-3, 1)                                 
    plt.ylabel("Amplitude")
    plt.title(f'{label} signal')
    plt.show()

# plot_raw_samples(samples)
plot_raw_samples(samples, True)

######################################################


t = np.linspace(0,1,fs)
test = np.array(np.cos(2*np.pi*40*t))


# fft_vals = fft.fft(hard_taps_arr)
# freq_bins = fft.fftfreq(N, T)


################## PLOT FFT ##################
fft_out = np.abs(rfft(filt_samples)) # Frequency Domain 
freq_bins = np.fft.rfftfreq(len(filt_samples), d=1/fs)

plt.plot(freq_bins, fft_out)    
plt.xlim(0, 1000)                                 
plt.xlabel("Frequency (Hz)")
plt.ylim(-3, 5E6)                                 
plt.ylabel("Amplitude")
plt.title(f'{name} fft')
# plt.show()

######################################################

# print(spectrum)
#filter out nonpostivite freq
# pos_mask = freq_bins > 0
# pos_freq = freq_bins[pos_mask]
