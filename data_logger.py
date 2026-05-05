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


# get the correct structure down!
# start byte: 0x7E
# end byte: 0x7F
START_byte1 = b'\xcd'
START_byte2 = b'\xab'
I2S_SAMPLE_RATE = 20000
# END = 0x7F
# MAX_LEN = 256

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
time.sleep(1)
sample_count = 1024
packet_size = sample_count * 2 # 2 bytes per sample

# logger = connect_python.get_logger(__name__)



def voltage_extractor(adc_signal):
    """ does the opposite of to_255; takes a signal from esp32 and makes it legible voltage value"""
    vref = 3.3 # volts
    return (adc_signal/4095) *vref # 12 bit resolution


def read_packet(duration_sec):
    """
    Makes sure packet is synchronized, well-formed, and not corrupt
    then returns this packet's data for processing.
    """

    total_samples = I2S_SAMPLE_RATE * duration_sec
    all_data= []
    print(f"Recording for {duration_sec} seconds")

    while len(all_data) < total_samples:
        
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
                all_data.extend(chunk)
    
    return np.array(all_data)
data = read_packet(3)
np.save('hydrophone_test_run.npy', data)
ser.close()
print("serial should be closed!")


time.sleep(1)

data = np.load('hydrophone_test_run.npy')

fs = 20000
time = np.linspace(0, len(data)/fs, num=len(data))

# plot
plt.plot(time,data)
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

def decode_adc_packet(payload):
    """
    extract the data and change it from little endian into correct format
    return the data and which channel it came from
    
    :param payload: the received message
    """
    # things to actually read what we're getting
    pkt_type = payload[0]
    ch = payload[1]
    samples=[]
    for i in range(2, len(payload), 2):
        samples.append(payload[i] | (payload[i+1]<<8))
    return ch, samples



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
