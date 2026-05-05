#include <Arduino.h>
#include <driver/i2s.h>


// now we are actually going to try sampling at higher frequencies!
#define I2S_SAMPLE_RATE 20000
#define BUF_LEN 1024 // is this even reasonable
#define BUF_COUNT 8 // have 4 buffers
#define ADC_INPUT ADC1_CHANNEL_6 // this is gpio 34
#define SAMPLES 0 
#define PKT_TYPE_ADC 0x01


// my ping-pong buffer implementation
#define SAMPLES_PER_BUFFER BUF_LEN
uint16_t buffer1[SAMPLES_PER_BUFFER];
uint16_t buffer2[SAMPLES_PER_BUFFER];
int active_buffer = 0;

unsigned long last_millis=0;
unsigned long total_samples=0;


// STUFF FOR STREAMING

// void send_ADC_packet() {
//   /*
//   This prepares the actual data in the packet
//   grabs 16 samples of data per message
//   */
//   uint8_t payload[2+SAMPLES*2];


//   payload[0] = PKT_TYPE_ADC;
//   payload[1] = 0; // channel for first probe


//  // payload: [ type ][ ch ][ s0_lo ][ s0_hi ] [ s1_lo ][ s1_hi ] ...

//   for (int i =0; i<SAMPLES; i++){
//     uint16_t v = analogRead(ADC_PIN_1); //  TODO --- NEED TO GRAB THE DATA FROM THE BUFFERS INSTEAD, AND CHANGE SENDING LENGTH ****************************************

//     payload[2+ 2*i] = v & 0xFF;
//     payload[2 + 2*i + 1] = v >> 8;
//   }
//   send_packet(payload, sizeof(payload));
// }

// void handle_streaming() {
//   /*
//   decides when to send next data packet
//   */
//   if (!streaming) return;

//   unsigned long now = millis();
//   if (now - last_send >= SAMPLE_PERIOD_MS) { //  TODO --- NEED TO DESIGN A DIFFERENT METRIC FOR THE DATA ACQUISITION ****************************************
//     last_send=now; // probablyu will have a problem if last send not defined
//     send_ADC_packet();
//   }
// }

// uint8_t checksum(uint8_t *data, uint16_t len) {
//   uint8_t c = 0;
//   for (uint16_t i=0; i<len; i++){
//     c ^= data[i];
//   }
//   return c;
// }
// void send_packet(uint8_t *payload, uint16_t len) {
//   /*
//   puts the whole message together and writes it to serial
//   */
//   Serial.write(START_BYTE);
//   Serial.write((uint8_t*)&len, 2);
//   Serial.write(payload, len);
//   Serial.write(checksum(payload, len));
//   Serial.write(END_BYTE);
// }

// END STUFF FOR STREAMING 

void setup() {
  // put your setup code here, to run once:
  Serial.begin(921600);
  delay(2000); // wait for noise to flush from boot stage
  // analogReadResolution(12);
  i2s_driver_uninstall(I2S_NUM_0);


  i2s_config_t i2s_config = {
  .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_ADC_BUILT_IN),
  .sample_rate = I2S_SAMPLE_RATE,
  .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT, 
  .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT, // is this something I need to specify?
  .communication_format = I2S_COMM_FORMAT_STAND_I2S, // is this how I actually want it?
  .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1, // what's this
  .dma_buf_count = BUF_COUNT,
  .dma_buf_len = BUF_LEN,
  .use_apll = false,
  .tx_desc_auto_clear = false,
  .fixed_mclk = 0};


  esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  // install and start i2s driver
  // i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  if (err!=ESP_OK){
    Serial.printf("Failed to install I2S: %d\n", err);
  }

  // i2s_driver_install(I2S_NUM_0, &i2s_config, 4, &i2s_queue);
  // init ADC pad
  err = i2s_set_adc_mode(ADC_UNIT_1, ADC_INPUT); // is this right
  if (err!=ESP_OK){
    Serial.printf("Failed to set ADC mode: %d\n", err);
  }
  // now enable the adc
  i2s_adc_enable(I2S_NUM_0);
  Serial.println("I2S ADC Read test initializeed");
  

}

void loop() {
  // put your main code here, to run repeatedly:
  // uint16_t i2s_read_buff[BUF_LEN]; // make our buffer
  size_t bytes_read;
  uint16_t* current_ptr = (active_buffer==0) ? buffer1 : buffer2;

  esp_err_t result = i2s_read(I2S_NUM_0, current_ptr, BUF_LEN*2, &bytes_read, portMAX_DELAY);

  // total_samples+=(bytes_read/2);
  // if (millis()-last_millis>5000){
  //   // now want to check freq
  //   float actual_rate = total_samples/5.0;
  //   Serial.print("Target: 20000Hz | Actual: ");
  //   Serial.print(actual_rate);
  //   Serial.println(" Hz");
  //   total_samples=0;
  //   last_millis=millis();
  // }
  if (result==ESP_OK && bytes_read>0){
    // get the smapels from our buffer
    // ESP32 I2S-ADC data has its channel id in upper 4 bits

    // make a starting 2 bytes
    uint16_t sync_byte = 0xABCD;
    Serial.write((uint8_t*)&sync_byte, 2);

    // now dump the buffer into the serial
    Serial.write((uint8_t*)current_ptr, bytes_read);

    // swap buffers for next iteration
    active_buffer = (active_buffer==0) ? 1:0; 

    // delay(500);
  }
}
