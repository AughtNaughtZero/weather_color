# weather_color
This project utilizes a 6 x 16 matrix of RGB LEDs to visualize weather forecast data pulled from an API.

The Weather Color program is designed to fetch weather forecast data from an API in regular intervals, parse the data 
into temperature, pressure, humidity, wind speed, chance of precipitation, and weather condition arrays, and then colorize 
and display that data across a 6 x 16 LED matrix. The program will also generate the file log.txt which is used for general 
trouble shooting and data review. The file is destroyed at each program startup.

The apiboot.txt and weather_color.py files are intended to reside in the root the /home/pi directory and to be launched at startup by editing crontab with the instruction @reboot sudo python3 /home/pi/weather_color.py.

A tutorial for the complete project can be found at xxxx. The basic hardware and software setup can be found at https://learn.adafruit.com/neopixels-on-raspberry-pi. The NeoPixel library for the Raspberry Pi (rpi_ws281x library) can be found at https://github.com/jgarff. The weather data and API are provided by Weather Underground, LLC (WUL). An API key can be obtained at www.wunderground.com/weather/api.
