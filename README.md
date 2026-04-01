# USWD_1820

Wrote the name wrong, should be UWSD - underwater signal detection.

We'll start by doing our signal analysis in python so that we can get 
an understanding of how to process the signals `

Some research papers activated their hydrophone for 30-60 seconds every 15-30 min. (30/30 often paired)

Information to keep in mind:

Location: Woods Hole

Possible Aquatic Life:

- whales - 
    INFO: Humpbacks (especially March-Nov) seem to be much more present than other whales, but fin and mink, along with North Atlantic right are known to make a presence. 

    - [Humpback](https://onlinelibrary.wiley.com/doi/10.1111/brv.12309): make song calls usually from 100Hz-4kHz, harmonics to at least 24kHz, males usually call for 3-30min
    - [Fin](https://dosits.org/galleries/audio-gallery/marine-mammals/baleen-whales/fin-whale/):
    They make sounds often called "A notes", which are typically very low frequency (20Hz) pulses usually lasting <1s. These can have high-freq components centered at 85-140Hz.
    - [Minke](https://dosits.org/galleries/audio-gallery/marine-mammals/baleen-whales/minke-whales/#:~:text=Common%20minke%20whales%20found%20in,%2C%20lasting%2050%2D70%20msec.):
    A series of lower frequency thumps. They make repetitive sounds - a 100-500Hz "pulse train". Each grunt is generally 165 to 320 milliseconds long, most energy around 80-140Hz. The thumps are 100-200Hz lasting 50-70 milliseconds. They also note having seen a brief pulse at 1.3kHz followed by a 1.4kHz call changing freqs for 2.5 seconds
    - [North Atlantic](https://www.sciencedirect.com/science/article/pii/S0025326X21010778):
    Exhibit tonal and impulsive signals. Tonal are generally seen with a fundamental freq 50-600Hz and less than 5s, "though impulsive signals are much shorter and broadband". They have upcalls ressembling modulated upsweep - minimum freq 80Hz, avg max freq 3140Hz - average peak 190hz. Interesting note: this whale makes a lot of signals, one being a "gunshot" - these are extremely short signals from 20Hz-20kHz with an average peak freq of 1190hz for 0.01-0.17s - theorized to be produced internally.

- crustaceans 
    - lobsters 
    - snapping shrimp
    - INFO (focuses on snapping):
        [Source](https://pmc.ncbi.nlm.nih.gov/articles/PMC4711987/)
        During summer can reach 1500-2000 snaps per minute, <100 snaps during winter. Snap rates are positively correlated with water temp (r= 0.81-0.93). Generally very large signals, having been measured in excess of 190dB 1μPa at 1m. 

        Frequency: 1.5-20kHz

- Disruptive Acoustics (other sounds to be wary of) 
    - harbor seals {love to growl, snort, and chirp; this may appear across many frequencies, making it easy to mistake for snapping shrimp or sperm whale clicks on spectrogram}
    - Oyster Toadfish {make a steady low-frequency call, a steady, harmonic tone around 200-250 Hz; could be mistaken for a distant boat}
    - Sea Robins (more common in shallow waters) {
        hit their swim bladders to produce sounds resembling "barks, cackles, and growls"; this can usually have a frequency between 200Hz-1kHz, these rapid and erratic clicks may potentially trigger a detector looking for transient whale clicks and "pulses" from a propeller. 
    }