#include <Arduino.h>
#include "soc/gpio_reg.h"

const int pin_RD = 2; // gpio num
const int pin_A0 = 15;
const int pin_INT = 4;

// const int data_pins[4] = {26, 25, 33, 32}; // DB4, DB5, DB6, DB7 #MSB order
const uint32_t MASK_DB7 = (1ULL <<5); // pin 5
const uint32_t MASK_DB6 = (1ULL <<18); // pin 18
const uint32_t MASK_DB5 = (1ULL <<19); // pin 19
const uint32_t MASK_DB4 = (1ULL <<21); // pin 21

const uint32_t MASK_DB3 = (1ULL <<23); // pin 23
const uint32_t MASK_DB2 = (1ULL <<22); // pin 22
const uint32_t MASK_DB1 = (1ULL <<27); // pin 27
const uint32_t MASK_DB0 = (1ULL <<25); // pin 25


volatile bool data_ready = false;
volatile bool timer_triggered = false;
volatile int last_value = 0;
const int data_pins[8] = {16, 17, 22, 23, 21, 19, 18, 5}; // DB4, DB5, DB6, DB7 #LSB order

// change back to 18 later

void IRAM_ATTR onADCReady(){
  uint32_t reg0_31 = REG_READ(GPIO_IN_REG);
  int val=0;

  // extract bits and pack into 4 bit number
  if (reg0_31 & MASK_DB7) val |= (1<<7);
  if (reg0_31 & MASK_DB6) val |= (1<<6);
  if (reg0_31 & MASK_DB5) val |= (1<<5);
  if (reg0_31 & MASK_DB4) val |= (1<<4);
  if (reg0_31 & MASK_DB3) val |= (1<<3);
  if (reg0_31 & MASK_DB2) val |= (1<<2);
  if (reg0_31 & MASK_DB1) val |= (1<<1);
  if (reg0_31 & MASK_DB0) val |= (1<<0);

  last_value=val;
  data_ready=true;
}



hw_timer_t * timer = NULL;
void IRAM_ATTR onTimer(){
  timer_triggered=true;
}

const int SAMPLING_FREQ = 20000;
uint8_t sample_id = 0; // rolling counter for id
const uint16_t BUF_LEN = 1024; // 50 pairs

uint8_t buffer1[BUF_LEN*2]; //100 bytes total
uint8_t buffer2[BUF_LEN*2];
int active_buffer=0;
uint16_t buffer_index = 0;

uint8_t tx_buffer=0;
uint8_t block_id=0;

unsigned long last_block_time = 0;



void setup(){
  Serial.begin(921600); // start with something slow
  delay(50);

  pinMode(pin_RD, OUTPUT);
  pinMode(pin_A0, OUTPUT);
  pinMode(pin_INT, INPUT);

  // digitalWrite(pin_RD, HIGH); // idle high - triggers low
  GPIO.out_w1ts = (1 << pin_RD);

  for(int i=0; i<8; i++){
    pinMode(data_pins[i],INPUT);
  }

  attachInterrupt(digitalPinToInterrupt(pin_INT), onADCReady, FALLING);
  
  // timer setup 80MHz / 80 = 1Mhz (1 tick per micro second)
  timer = timerBegin(0,80,true);
  timerAttachInterrupt(timer, &onTimer, true);

  int freq_ratio = 1000000 / SAMPLING_FREQ;
  Serial.print(freq_ratio);

  timerAlarmWrite(timer,freq_ratio, true); //50 us = 20kHz
  timerAlarmEnable(timer);

  Serial.println("AD7824 4-bit test starting + interrupt ");

}

int read_channel(int channel) {
  data_ready = false;

  // digitalWrite(pin_A0, channel==0? LOW:HIGH);
  if (channel==0)GPIO.out_w1tc = (1<<pin_A0);else GPIO.out_w1ts = (1<<pin_A0); 

  //trigger conversion
  // digitalWrite(pin_RD, LOW);
  GPIO.out_w1tc = (1<<pin_RD);

  // we need to wait for INT to go low, conversion complete
  // in real TDOA script, we'll use interrupt, but pulling is safer for testing
  uint32_t timeout = 10000;
  while(!data_ready && timeout >0){
    timeout--;
  }

  // reset RD for next cycle
  // digitalWrite(pin_RD, HIGH);
  GPIO.out_w1ts = (1<<pin_RD);
  if (timeout==1){
    Serial.println("ADC TIMEOUT");
  }
  return last_value;
}

void loop() {
  // timer_triggered=false;
  // int freq_ratio = 1000000 / SAMPLING_FREQ;
  // Serial.print("freq ratio: ");
  // Serial.println(freq_ratio);
  if (timer_triggered){
    timer_triggered=false;
    uint8_t* current_ptr = (active_buffer==0)?buffer1:buffer2;

    current_ptr[buffer_index++] = (uint8_t)read_channel(0); // piezo 1 should be 3.3V
    current_ptr[buffer_index++] = (uint8_t)read_channel(1); // piezzo 2 should be 0V

    if (buffer_index >= (BUF_LEN*2)){
      uint8_t* send_ptr =current_ptr;
      active_buffer^=1;
      
      // buffer_ready=true;

      // unsigned long end_micros = micros();
      // unsigned long total_duration = end_micros - last_block_time;
      // last_block_time = end_micros;
      // // Serial.print("Block duration (us)");
      // Serial.println(total_duration);


      uint8_t checksum=0;
      buffer_index=0;

      for (int i=0; i<(BUF_LEN*2); i++){
        checksum^= send_ptr[i];
      }
      checksum^= 0x00;

      Serial.write(0xAA); // start byte
      Serial.write(block_id);
      Serial.write(send_ptr, BUF_LEN*2);
      Serial.write(0x00); // end byte
      Serial.write(checksum);

      block_id++;
    }

    // Serial.write(sample_id);
    // Serial.write(p1);
    // Serial.write(p2);
    // Serial.write();

    // sample_id++;



  }

}