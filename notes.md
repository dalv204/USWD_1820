Seems like a tap registers around 200Hz

knock is somewhere between 300 and 500 Hz


looking at data, a peak is very jagged, 
so we'll likely want to apply a bit of smoothing there to accurately find peaks


if we want to send data only for when we have a peak, then we need to have the 
esp32 collect a running peak-average calc 

