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
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter, medfilt

ser = serial.Serial('COM3', 921600, timeout=1)
time.sleep(.5)


START_byte1 = b'\xaa'
START_byte2 = b'\xab'
END_byte1 = b'\x00'
SAMPLE_RATE = 80000
BUF_LEN = 50 # 50 pairs

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

    piezo1_total = np.array([])
    piezo2_total = np.array([])

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

            piezo1_total = np.append(piezo1_total, piezo1)
            piezo2_total = np.append(piezo2_total, piezo2)

            # print(len(piezo1))
            all_data += len(piezo1)*2
    
    return piezo1_total, piezo2_total



a_data, b_data = read_packet(5)
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
    


    max_peak = np.max(peaks)
    max_peak_locations = np.where(np.abs(filt_sig)>=max_peak)
    avg_peak = np.average(peaks)
    print(f"average peak is {avg_peak}")
    general_peak_locations = np.where(filt_sig>avg_peak)
    general_peak_values = np.array([filt_sig[i] for i in general_peak_locations[0]])

    true_peak_locations,_ = signal.find_peaks(np.abs(general_peak_values), height=0,distance=1)

    # print(f"these are the max peaks: {max_peak_locations}")
    # print(f" at values {[filt_sig[i] for i in max_peak_locations]}")
    # print(f"there are {len(true_peak_locations)} peaks calculated")

    # return [general_peak_locations[0][i] for i in true_peak_locations]
    # return max_peak_locations[0]
    return general_peak_locations[0]



# code for correlation!

def calculate_localization(sig_a, sig_b, fs = SAMPLE_RATE, v_wood=4950):  #v_wood based on trials
    """ 
    uses input from both signals to calculate the time difference and thus return localization (1D) 

    sig_a is coming from the left (should mark)
    sig_b is coming from the right 
    fs is sampling freq
    v-wood is the sound in the wood (m/s) - we should calibrate this
    """

    # steps

    # 1 pre-processing: remove DC offset and any fuzz that we can
    # data = savgol_filter(data-np.mean(data), window_length=50, polyorder=3)

    sig_a_smooth = sig_a# gaussian_filter1d(sig_a-np.mean(sig_a),sigma=2)
    sig_b_smooth = sig_b#gaussian_filter1d(sig_b-np.mean(sig_b),sigma=2)

    # new_sig = gaussian_filter1d(sig_a-np.mean(sig_a),sigma=1.5, order=1)
    # plt.plot(list(range(len(new_sig))), new_sig)
    # plt.show()
    # segment_length = 1000 # samples per length

    # peaks = np.array([np.max(np.abs(sig_a_smooth[i:i+segment_length])) for i 
    #                 in range(0,len(sig_a_smooth),segment_length)])

    # avg_peak = np.average(peaks)
    # indices_a = np.where(np.abs(sig_a_smooth)>avg_peak)[0]

    indices_a = peak_localization(sig_a_smooth)
    if indices_a is None or len(indices_a)==0:
        # no tap detected?
        return None,None
    print(f"indices are {indices_a}")
    start_idx = max(0, indices_a[0]-100) # include some pre-trigger
    end_idx = min(len(sig_a_smooth), indices_a[0]+10) # short window?
    # now we want ot get the windows
    a_win = sig_a_smooth[start_idx:end_idx]
    b_win = sig_b_smooth[start_idx:end_idx]
    # print(f"start index {start_idx}")
    # print(f"end index {end_idx}")
    plt.plot(list(range(len(a_win))), a_win)
    plt.plot(list(range(len(a_win))), b_win)
    plt.show()


    # print(f"len sig_a {len(sig_a)}")
    # print(f"len sig_b {len(sig_b)}")

    # print(len(a_win))
    # print(len(b_win))
    # 2 do cross correlation (extract initial time stamp (or just always send with the same start!))
    a_der = np.gradient(a_win)
    b_der = np.gradient(b_win)

    # in 'full' mode will return array of length len(a) + len(b) - 1
    corr = signal.correlate(a_der, b_der, mode='full')

    # 3 find the peak, 'zero lag' is at the center of full correlation array 
        #   (do we want the peak, or the tiny drop before it?)
    
    center = len(a_win) -1 
    k_int = np.argmax(np.abs(corr))
    print(f"k_int location is {k_int}")

    # 4 is sub-sample parabolic interpolation necessary? - make sure to check boundaries for edge conditions

    # TODO - ignore this for now!

    # 5 convert the peak index into a time delay between both signals
        #   make the distance relative to the center of the wood piece

    peak_time_offset = k_int - center
    dt = (peak_time_offset/fs) - 2.5e-6 
    print(f"dt is {dt:.15f}")
    # d1 = ((SENSOR_DIST - dt*v_wood)/2.0)*100 # distance to sensor on right (cm)
    d1 = ((dt*v_wood)/2.0)*100 # distance to sensor on right (cm)


    return d1, corr

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
# a_data = gaussian_filter1d(a_data,sigma=1.5, order=1)
# b_data = gaussian_filter1d(b_data,sigma=1.5, order=1)



# def remove_glitches(data, max_diff=50)

print(peak_localization(a_data))
local_data = calculate_localization(a_data,b_data)
print(f"about {local_data[0]}cm from center")
plt.plot(list(range(len(local_data[1]))), local_data[1], label="correlation")
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












    
    # raw_len = read_exact(2)
    # length = struct.unpack("<H", raw_len)[0]
    # if length>MAX_LEN:
    #     logger.error("Data of bad length!") # normally want to handle gracefully, here have it just stop so we can see the error clearly

    #     raise RuntimeError("Bad Length") # error for misread
    
    # # print(f"{length=}")
    # payload = read_exact(length)
    # check_byte = read_exact(1)[0]
    # end = read_exact(1)[0]

    # if end!=END:
    #     logger.error("Bad end byte")

    #     raise RuntimeError("Bad end byte") # error for corruptino
    
    # calc = 0 
    # for b in payload:
    #     calc ^=b
    # if check_byte!=calc:
    #     logger.error("Checksum Error")

    #     return RuntimeError("Checksum Error") # error for corruption
    
    # return payload

# def decode_adc_packet(payload):
#     """
#     extract the data and change it from little endian into correct format
#     return the data and which channel it came from
    
#     :param payload: the received message
#     """
#     # things to actually read what we're getting
#     pkt_type = payload[0]
#     ch = payload[1]
#     samples=[]
#     for i in range(2, len(payload), 2):
#         samples.append(payload[i] | (payload[i+1]<<8))
#     return ch, samples



# send_cmd(ADC_STREAMING)
# send_cmd(0x03, [0x00, 10])
# ser.reset_input_buffer()


# payload = read_packet()

# pkt_type = payload[0]
# ch = payload[1]

# if pkt_type ==0x01:
#     samples=[]
#     for i in range(2,len(payload), 2):
#         samples.append(payload[i] | (payload[i+1]<<8))

#     print("ADC:", samples[:5], "...")


# def update_wave_gen(client,wave_amp, wave_offset, wave_freq, wave_type, wave_en):
#     """ 
#     check whether one of the wavegen params have changed
#     compare new values to old values to decide if a new message must be sent
#     """
#     new_amp = client.get_value("amplitude")
#     new_offset = client.get_value("offset")
#     new_type = client.get_value("wave_type")
#     new_enable = client.get_value("gen_enable_box")
#     new_freq = client.get_value("frequency")
#     new_values = [new_amp, new_offset, new_type, new_freq, new_enable]
#     old_values = [wave_amp, wave_offset, wave_type, wave_freq, wave_en]
#     resend_wave = False
#     for i in range(len(new_values)):
#         if old_values[i]!=new_values[i]:
#             # set resend true, return all new values
#             resend_wave=True
#             return (resend_wave,)+tuple(new_values)
#     return (resend_wave,)+tuple(old_values)
    

#                             # math_op = calculate(ch1_val, ch2_val, V1,V2 op)

# def calculate(ch1_val, ch2_val, V1, V2, op):
#     """
#     Docstring for calculate
    
#     :param ch1_val: value from channel 1
#     :param ch2_val: chanel 2 value
#     :param V1: value a in eq
#     :param V2: value b in eq
#     :param op: operation
#     """
#     op_dict = {"Add": lambda a,b: a+b, "Sub":lambda a,b: a-b, "Mul":lambda a,b: a*b, "Div": lambda a,b: a/b if b!=0 else 0}
#     variable_dict = {"CH1":ch1_val, "CH2":ch2_val}

#     return op_dict[op](variable_dict[V1], variable_dict[V2])


# @connect_python.main
# def stream_data(client: connect_python.Client):
#     """
#     this stays connected the whole time, manages behavior between the GUI and the esp32
#     also handles errors, not necessarily gracefully

#     """

#     # default wave setup 
#     wave_amp = 0
#     wave_offset=0
#     wave_freq=0
#     wave_type=""
#     resend_wave=False
#     wave_gen_enable=False
#     math_enabled=False
#     sent_error_message=False

#     # initialize my stream :)
#     client.clear_stream("adc_stream")
#     current_packets=[None,None]
#     try:
#         while True:
#             # how to grab info from sliders, drop down, and checkbox
#             if client.get_value("stream_enable"):
#                 # if we are streaming, check if we have updated our wave_gen requirement
#                 resend_wave,wave_amp, wave_offset, wave_type, wave_freq, wave_gen_enable = update_wave_gen(client, wave_amp, wave_offset, wave_freq, wave_type, wave_gen_enable)
#                 if resend_wave:
#                     # if there has been a change, send it to the esp32
#                     logger.info("new_change")
#                     set_waveform(type=wave_type, frequency=wave_freq, amplitude=wave_amp, offset=wave_offset, wave_gen_enable=wave_gen_enable)
                
#                 # read incoming data

#                 pkt = read_packet()
#                 pkt_type = pkt[0]
#                 if pkt_type == 0x01: #adc signal
#                     ch, samples = decode_adc_packet(pkt)
#                     current_packets[ch]=samples

#                     # get the timestamp for each sample
#                     if all(x is not None for x in current_packets): # check if we have data from all channels
#                         timestamp = datetime.now()
#                         for i in range(len(samples)): # now get to streaming each of them
#                             ch1_val = float(voltage_extractor(current_packets[0][i])) # convert into voltage reading for GUI
#                             ch2_val = float(voltage_extractor(current_packets[1][i]))
#                             if client.get_value("math_enable_box"):
#                                 # if math is enabled, display it!
#                                 math_enabled=True
                                
#                                 op = client.get_value("Op")
#                                 v1 = client.get_value("V1")
#                                 v2 = client.get_value("V2")
#                                 try:
#                                     if (x is not None for x in (op, v1,v2)):
#                                         math_result = calculate(ch1_val, ch2_val, v1, v2, op)
#                                         sent_error_message=False # will reach this if doesn't error 

#                                         client.stream("adc_stream", timestamp, names=["CH1", "CH2", "M"], 
#                                                 values=[ch1_val, ch2_val, math_result])
#                                 except Exception as e:
#                                     # error if math is enabled without declaring the type
#                                     if not sent_error_message:
#                                         logger.error("SET MATH PARAMETERS")
#                                         sent_error_message=True # only want to send the message once
#                                     client.stream("adc_stream", timestamp, names=["CH1", "CH2"], 
#                                             values=[ch1_val, ch2_val])
#                             else:
#                                 # clear the stream if we have disabled the math box
#                                 if math_enabled:
#                                     math_enabled=False
#                                     client.clear_stream("adc_stream")
#                                 client.stream("adc_stream", timestamp, names=["CH1", "CH2"], 
#                                             values=[ch1_val, ch2_val])
#                         current_packets=[None,None]
#                         # time.sleep(0.001) # do we want a delay for the gui to update?
#     except Exception as e:
#         print(f"Error: {e}")
   
# if __name__ == "__main__":
#     logger.info("Initiating Oscilloscope")

#     stream_data()

# ------------------------------------------------------------------------------------------------


# ignore stuff below! :)






 # # Initialize state variables from initial app state
    # frequency = client.get_value("frequency", 5.0)
    # y_offset = client.get_value("y_axis_offset", 0.0)
    # connection_rid = client.get_value("connection_rid", "")
    # channel = client.get_value("channel", "")
    # tag_key = client.get_value("tag_key", "")
    # tag_value = client.get_value("tag_value", "")
    # stream_to_nominal = client.get_value("stream_to_nominal", False)

    # logger.info(f"Initial values - frequency: {frequency}, y_offset: {y_offset}")

    # connection = nm.get_connection(connection_rid) if connection_rid else None
    # write_stream = connection.get_write_stream(batch_size=1) if connection else None

    # if not write_stream and stream_to_nominal:
    #     logger.error("Error: streaming not configured!")
    #     exit(1)

    # try:
    #     # clear the streams used by this script
    #     client.clear_stream("sine_wave")
    #     client.clear_stream("cosine_wave")
    #     client.clear_stream("tangent_wave")

    #     start = time.time()
    #     last_log_time = time.time()

    #     while True:
    #         t = time.time()
    #         delta = time.time() - start
    #         sine = np.sin(delta * frequency) + y_offset
    #         cosine = np.cos(delta * frequency) + y_offset
    #         tangent = np.tan(delta * frequency) + y_offset

    #         # Log values once per second
    #         current_time = time.time()
    #         if current_time - last_log_time >= 1.0:
    #             color = GREEN if tangent >= 0 else RED
    #             logger.info(f"Tangent value: {color}{tangent:.3f}{RESET}")
    #             last_log_time = current_time

    #         client.stream("sine_wave", t, float(sine))
    #         client.stream("cosine_wave", t, float(cosine))
    #         client.stream("tangent_wave", t, float(tangent)) #-- ignore this, just a simulation type ting

    #         if write_stream:
    #             tags = None
    #             if tag_key and tag_value:
    #                 tags = {tag_key: tag_value}

    #             write_stream.enqueue(
    #                 channel_name=channel if channel else "Unnamed_channel",
    #                 timestamp=datetime.now(),
    #                 value=float(sine),
    #                 tags=tags,
    #             )
    #         time.sleep(0.015)  # Add a small delay
    # except Exception as e:
    #     logger.error(f"Error: {e}")
# def sync_toit():
#     window = b""
#     while True:
#         byte=ser.read(1)
#         if not byte:
#             continue
#         window = (window+byte)[-4:]
#         if window==b"CBOR":
#             print("returned")
#             return
# def read_packet():
#     # get the packet read :)
#     sync_toit()
    
#     raw_len = read_exact(4)
    
#     length = struct.unpack("<I", raw_len)[0]
#     payload = read_exact(length)
#     print("Payload bytes:", payload[:8])
#     # if len(payload)!=length:
#     #     raise RuntimeError("TIMEOUT READING PAYLOAD")
#     return cbor2.loads(payload)

# while True:
#     pkt = read_packet()
#     print(pkt)
#     if pkt:
#         if pkt["type"] =="adc":
#             print(f"ADC ch{pkt['ch']} @ {pkt['ts_ms']} ms:",
#                 pkt["samples"][:5], "...")
