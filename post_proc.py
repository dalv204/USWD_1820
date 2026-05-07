import numpy as np
import numpy.fft as fft
import math
import matplotlib.pyplot as plt

hard_taps_arr = np.array(np.load("tests/hard_taps_noisy.npy"))
knocks_arr = np.load("tests/knocks_noisy.npy")

samples = knocks_arr

fs = 44100 # Hz
T = 1.0/fs
N = len(samples) # num samples
t = np.linspace(0.0, N*T)

t = np.linspace(0,1,fs)
test = np.array(np.cos(2*np.pi*40*t))


# fft_vals = fft.fft(hard_taps_arr)
# freq_bins = fft.fftfreq(N, T)

#filter out nonpostivite freq
# pos_mask = freq_bins > 0
# pos_freq = freq_bins[pos_mask]


fft_out = np.abs(np.fft.rfft(samples)) # Frequency Domain 
fft
freq_bins = np.fft.rfftfreq(len(samples), d=1/fs)

plt.plot(freq_bins, fft_out)    
plt.xlim(0, 300)                                 
plt.xlabel("Frequency (Hz)")
# plt.ylim(-3, 1)                                 
plt.ylabel("Amplitude")
plt.title("Knocks")
plt.show()
# print(spectrum)
