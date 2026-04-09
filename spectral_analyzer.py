# now that we have some good audios to start with... how should we proceed...

# running some FFTs to start could be good to get an undersatnding of what 
# frequencies to expect, but I don't think we should necessarily use an FFT 
# on the actual deployable  

import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display

def analyze_audio_sparsity(file_path, threshold_db = -50): # change this latr - what should this be? 
    # get this audio file in here
    # sr = None just preserved our original sampling rate
    
    # this seems flawed, a lot of the sounds may have low decibel sounds, and therefore makes the calc
    # "sparse"
    print("this is basic")
    y, sr = librosa.load(file_path, sr=None)

    # get our fft (make it short?)
    # n_fft is our window size, hop_length is the stride
    D = librosa.stft(y, n_fft=2048, hop_length=512)
    print(D)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

    # produce a sparsity score
    total_bins = S_db.size
    print(f'{total_bins=}')
    sig_bins = np.sum(S_db>threshold_db) # these are bins that have good stuff in them
    print(f"{sig_bins=}")
    sparsity_percentage = 100 * (1-(sig_bins/total_bins))
    
    print("am I here")
    # now let's plot this
    plt.figure(figsize=(12,8))

    # spectrogram
    ax = plt.subplot(2,1,1)
    librosa.display.specshow(S_db, sr=sr, hop_length=512, x_axis='time', y_axis='hz')

    plt.colorbar(format='%+2.0f dB')
    plt.title(f'Spectrogram: {file_path}')
    plt.ylim(0, 50000) # focus on 0-50kHz (may change, not sure what to expect yet)

    # now we also want to plot a power spectral density (average energy across freq)
    plt.subplot(2,1,2)
    psd = np.mean(S_db, axis=1)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    plt.plot(freqs, psd)
    plt.axhline(y=threshold_db, color='r', linestyle='--', label='Sparsity Threshold')
    plt.title(f'Power Spectral Density (average energt)')
    plt.xlabel('frequency (hz)')
    plt.ylabel('average dB')
    plt.xlim(0,50000)
    plt.legend()
    print("here")

    plt.tight_layout()

    print(f"{sparsity_percentage=}")

    # add a little spectrogram annotation 
    ax.annotate(f'Freq Sparsity %: {sparsity_percentage}', xy=(2, 5000), xytext=(3,5000),color='white')

    plt.show()
    print("should be showing")
    # maybe put some print statements here?

    return sparsity_percentage

print("ok")

seal_sounds = 'audios/seals/HS_and_snapshrimp_noisy_2.wav'
whale_sounds = 'audios/whales/humpback/humpback_noisy_1.wav'
NAR_sounds = 'audios/whales/NAR/NAR_gunshot_1.wav'

print(analyze_audio_sparsity(NAR_sounds))


# we have a hydrophone and need to collect data well below nyquist freq - so 


# questions:

# 1. I'm not sure how to classify what as significant
# 2. how do I make it recognize these complex calls, that span many freqs (but nonetheless a clear signal)
# 3. I think the lower frequencies are always generally louder, we can't just count interesting sounds as the loudest ones
    # how do we get this to WANT to reconstruct complex, quieter patterns...
# 4. I don't think the Power Spectral Density (average energy) tells us anything... 
    # there's almost always a higher energy seen from the lower (on average)