notes on sparsity:

seems like we are looking for this to have some sort of sparsity, whether it be some temporal or spatial sparsity (time domain vs frequency domain sparsity)

steps: 
1. we want to do a time-frequency analysis of our current signals (spectrograms)
    - I think it would be good to chop up the signal into segments (this is not making it sparser, just separating it), and take a shorter form of a FT
    - this will give us a better idea of what our features look like
    - making a long window can give us better frequency resolution, but may also cause spectral blurring for quick snaps like the shrimp

2. sub-nyquist sampling is difficult, because it will lead to aliasing, which makes deciphering signals harder
    - seems that the more sparse a signal is, the more aggressively we can subsample without losing information
    - May want to look into the following:
        - Non-Uniform Sampling (NUS) / Jittered Sampling
        - Random Demodulator (RD)
        - Finite Rate of Innovation (FRI)
            - based on listening for amplitudes, which may be good for things that make 'clicking' sounds

        - Orthogonal Matching Pursuit (OMP) algorithm

        - [Compressed Sampling](https://ieeexplore.ieee.org/document/8395390)
            - this source seems to suggest that underwater signals are not sparse in time domain.

notes on LM recognition: