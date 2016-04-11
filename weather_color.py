# weather_color.py
#
# This project utilizes a 6 x 16 matrix of RGB LEDs to visualize weather forecast data pulled from an API.
#
# The Weather Color program is designed to fetch weather forecast data from an API in regular intervals, parse the data 
# into temperature, pressure, humidity, wind speed, chance of precipitation, and weather condition arrays, and then colorize 
# and display that data across a 6 x 16 LED matrix. The program will also generate the file log.txt which is used for general 
# trouble shooting and data review. The file is destroyed at each program startup.
# 
# The apiboot.txt and weather_color.py files are intended to reside at /home/pi/weather_color directory and to be launched at 
# startup by editing crontab with the instruction @reboot sudo python3 /home/pi/weather_color/weather_color.py.
# 
# A tutorial for the complete project can be found at xxxx. The basic hardware and software setup can be found at
# https://learn.adafruit.com/neopixels-on-raspberry-pi. The NeoPixel library for the Raspberry Pi (rpi_ws281x library) can be 
# found at https://github.com/jgarff. The weather data and API are provided by Weather Underground, LLC (WUL). An API key can 
# be obtained at www.wunderground.com/weather/api.

import time
import json
from urllib.request import urlopen
from neopixel import *

# LED strip configuration:
STRIP_COUNT    = 16                 # Number of LED pixels represented for each weather data set.
LED_COUNT      = 96                 # Total number of LED pixels.
LED_PIN        = 18                 # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ    = 800000             # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 5                  # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS = 10                 # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False              # True to invert the signal (when using NPN transistor level shift)

# other constants
OBJMAX = 32                         # set max number of objects to parse from weather data
HOURMULT = 2                        # set multiplier for LED hour representation
RMULT = 1                           # multiplier to adjust for red LED brightness
GMULT = .8                          # multiplier to adjust for green LED brightness
BMULT = .8                          # multiplier to adjust for blue LED brightness
COLORVAL = 10                       # set max number for color array
BLUE = 2                            # RGB blue truncate value
PATH_NAME = "//home//pi//weather_color//"  # set path to find apiboot.txt and log.txt files
TEMPMIN = 0                         # minimum value for normalized temperature range
TEMPMAX = 100                       # maximum value for normalized temperature range
TEMPDELTA = TEMPMAX - TEMPMIN       # delta value for normalized temperature range
PRESSMIN = 29.0                     # minimum value for normalized pressure range
PRESSMAX = 30.8                     # maximum value for normalized pressure range
PRESSDELTA = PRESSMAX - PRESSMIN    # delta value for normalized pressure range
HUMIDMIN = 5                        # minimum value for normalized humidity range
HUMIDMAX = 95                       # maximum value for normalized humidity range
HUMIDDELTA = HUMIDMAX - HUMIDMIN    # delta value for normalized humidity range
PRECIPMIN = 5                       # minimum value for normalized precipitation range
PRECIPMAX = 95                      # maximum value for normalized precipitation range
PRECIPDELTA = PRECIPMAX - PRECIPMIN # delta value for normalized precipitation range
WINDMIN = 5                         # minimum value for normalized wind speed range
WINDMAX = 45                        # maximum value for normalized wind speed range
WINDDELTA = WINDMAX - WINDMIN       # delta value for normalized wind speed range
TIME_BETWEEN_CALLS = 900            # time in seconds between calls to the weather api
TIME_BETWEEN_FAILED = 180           # time in seconds between failed calls to the weather api
TIME_WAIT_STARTUP = 60              # time in seconds to wait after bootup to make first call

def readApiBootFile():
    # opens apiboot.txt file and reads the api key (obtain from weather underground), state (IN), and city (Indianapolis)
    # from the first three lines of the file, ignoring the '#' for comments
    i = 0
    a = [None]*2
    try:
        textFile = open(PATH_NAME + "apiboot.txt", "r")
        while i < 2:
            a[i] = textFile.readline().rstrip('\n')
            if a[i][0] != "#":
                i += 1
    except:
        textFile = open(PATH_NAME + "log.txt", "w")
        textFile.write("Failed to read apiboot.txt file. Check that file exists and contains the three lines: \n-your-api-key-\n-your-state-\n-your-city-")
        textFile.close()
    else:
        textFile.close()
        return a

def writeLogFile(text, mode):
    # writes information to log.txt file
    textFile = open(PATH_NAME + "log.txt", mode)
    textFile.write(text)
    textFile.close()

def colorWipe(strip, color, wait_ms=10):
    # wipe color across display a pixel at a time
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        time.sleep(wait_ms/1000.0)
    strip.show()

def wheel(pos):
    # generate rainbow colors across 0-255 positions
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow(strip, wait_ms=10, iterations=17):
    # draw rainbow that fades across all pixels at once
    # iterations set to 30 which roughly corresponds to the TIME_WAIT_START constant
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i+j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def colorSet(strip, weatherData, pinAdd, wait_ms=10):
    # wipe weather colors across entire display one pixel at a time in designated hour increments
    # RGB color array contains 'heat map' gradients
    colors = {0:[255,0,255],
         1:[125,0,255],
         2:[0,0,255],
         3:[0,125,255],
         4:[0,255,255],
         5:[0,255,125],
         6:[0,255,0],
         7:[125,255,0],
         8:[255,255,0],
         9:[255,125,0],
         10:[255,0,0]}
    for i in range(STRIP_COUNT):
        # color values passed to setPixelColor are GRB not RGB
        strip.setPixelColor(i+pinAdd, Color(int((colors[weatherData[i*HOURMULT]][1])*GMULT),int((colors[weatherData[i*HOURMULT]][0])*RMULT),int((colors[weatherData[i*HOURMULT]][2])*BMULT)))
        time.sleep(wait_ms/1000.0)
    strip.show()

def scrollArray(strip, weatherData, wait_ms=200):
    # wipe historical weather data from right to left across the strip
    # this function needs more work and is currently not called in this weather_color version
    # a = [1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7,7,8,8,8,9,9,9,10,10,10,1,1,1,2,2,2]
    temp = [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8]
    colors = {0:[255,0,255],
     1:[125,0,255],
     2:[0,0,255],
     3:[0,125,255],
     4:[0,255,255],
     5:[0,255,125],
     6:[0,255,0],
     7:[125,255,0],
     8:[255,255,0],
     9:[255,125,0],
     10:[255,0,0]}
    for i in range(0,OBJMAX,1):
        del temp[0]
        temp.append(a[i])
        for j in range(STRIP_COUNT - 1,-1,-1):
            strip.setPixelColor(j, Color(int((colors[temp[j]][1])),int((colors[temp[j]][0])),int((colors[temp[j]][2]))))
        strip.show()
        time.sleep(wait_ms/1000.0)

def parseWeatherData(obj):
    # parse data obtained from the weather api
    temp = [None]*OBJMAX                # array to hold temperature values
    press = [None]*OBJMAX               # array to hold pressure values
    humid = [None]*OBJMAX               # array to hold humidity values
    precip = [None]*OBJMAX              # array to hold precipitation (probability of) values
    wind = [None]*OBJMAX                # array to hold wind speed values
    fct = [None]*OBJMAX                 # array to hold coded weather condition values
    fcttime = [None]*OBJMAX             # array to hold time of forecast
    for i in range(OBJMAX):
        temp[i] = int(obj["hourly_forecast"][i]["temp"]["english"])
        press[i] = float(obj["hourly_forecast"][i]["mslp"]["english"])
        humid[i] = int(obj["hourly_forecast"][i]["humidity"])
        precip[i] = int(obj["hourly_forecast"][i]["pop"])
        wind[i] = int(obj["hourly_forecast"][i]["wspd"]["english"])
        fct[i] = int(obj["hourly_forecast"][i]["fctcode"])
        fcttime[i] = str(obj["hourly_forecast"][i]["FCTTIME"]["civil"])
    return temp, press, humid, precip, wind, fct, fcttime

def colorAssign(temp, press, humid, precip, wind, fct):
    # assign color values to weather data
    tempClr = [None]*OBJMAX                # array to hold temperature values
    pressClr = [None]*OBJMAX               # array to hold pressure values
    humidClr = [None]*OBJMAX               # array to hold humidity values
    precipClr = [None]*OBJMAX              # array to hold precipitation (probability of) values
    windClr = [None]*OBJMAX                # array to hold wind speed values
    fctClr = [None]*OBJMAX                 # array to hold coded weather condition values
    for i in range(OBJMAX):
        # assign color values for temperature data
        if temp[i] <= 0:
            tempClr[i] = 5
        elif temp[i] > 5 and temp[i] <= 15:
            tempClr[i] = 0
        elif temp[i] > 15 and temp[i] <= 25:
            tempClr[i] = 1
        elif temp[i] > 25 and temp[i] <= 35:
            tempClr[i] = 2
        elif temp[i] > 35 and temp[i] <= 45:
            tempClr[i] = 3
        elif temp[i] > 45 and temp[i] <= 55:
            tempClr[i] = 4
        elif temp[i] > 55 and temp[i] <= 65:
            tempClr[i] = 5
        elif temp[i] > 65 and temp[i] <= 75:
            tempClr[i] = 6
        elif temp[i] > 75 and temp[i] <= 85:
            tempClr[i] = 7
        elif temp[i] > 85 and temp[i] <= 95:
            tempClr[i] = 8
        elif temp[i] > 95 and temp[i] <= 105:
            tempClr[i] = 9
        else:
            tempClr[i] = 10
        
        # normalize color values for pressure data
        if press[i] <= PRESSMIN:
            pressClr[i] = 0
        elif press[i] >= PRESSMAX:
            pressClr[i] = COLORVAL
        else:
            pressClr[i] = int(COLORVAL*((press[i] - PRESSMIN)/(PRESSDELTA)))
            
        # normalize color values for humidity data - except truncate low values to RGB blue
        if humid[i] <= HUMIDMIN:
            humidClr[i] = BLUE
        elif humid[i] >= HUMIDMAX:
            humidClr[i] = COLORVAL
        else:
            humidClr[i] = int(BLUE + (COLORVAL - BLUE)*((humid[i] - HUMIDMIN)/(HUMIDDELTA)))

        # normalize color values for precipation data - except truncate low values to RGB blue
        if precip[i] <= PRECIPMIN:
            precipClr[i] = BLUE
        elif precip[i] >= PRECIPMAX:
            precipClr[i] = COLORVAL
        else:
            precipClr[i] = int(BLUE + (COLORVAL - BLUE)*((precip[i] - PRECIPMIN)/(PRECIPDELTA)))

        # normalize color values for wind speed data - except truncate low values to RGB blue
        if wind[i] <= WINDMIN:
            windClr[i] = BLUE
        elif wind[i] >= WINDMAX:
            windClr[i] = COLORVAL
        else:
            windClr[i] = int(BLUE + (COLORVAL - BLUE)*((wind[i] - WINDMIN)/(WINDDELTA)))

        # assign color values to forecast codes
        if fct[i] == 1:
            fctClr[i] = 6
        elif fct[i] == 2:
            fctClr[i] = 5
        elif fct[i] == 3:
            fctClr[i] = 4
        elif fct[i] == 4 or fct[i] == 5 or fct[i] == 6 or fct[i] == 18 or fct[i] == 20:
            fctClr[i] = 3
        elif fct[i] == 19 or fct[i] == 21:
            fctClr[i] = 2
        elif fct[i] == 10 or fct[i] == 12:
            fctClr[i] = 8
        elif fct[i] == 7 or fct[i] == 11 or fct[i] == 13:
            fctClr[i] = 9
        elif fct[i] == 14 or fct[i] == 15 or fct[i] == 24:
            fctClr[i] = 10
        elif fct[i] == 16:
            fctClr[i] = 1
        elif fct[i] == 8 or fct[i] == 9 or fct[i] == 22 or fct[i] == 23:
            fctClr[i] = 0
        else:
            fctClr[i] = 6
            
    return tempClr, pressClr, humidClr, precipClr, windClr, fctClr

def main():
    # Create NeoPixel object with appropriate configuration.
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    startTime = time.time()             # set beginning for time between weather updates
    elapsedTime = 0.1                   # set initial elapsed time between weather updates
    boot = True                         # boot bit is used for tracking first call after start up
    success = False                     # success bit is used for tracking the success or failure of api calls
    loopCount = 0                       # set intial count of api calls
    writeLogFile('-----Initializing-----', 'w')
    rainbow(strip)                      # initialize LED strip to rainbow cycle
    apiVal = readApiBootFile()
    apiUrl = "http://api.wunderground.com/api/" + str(apiVal[0]) + "/hourly/q/" + str(apiVal[1]) + ".json"
    while loopCount >= 0:
        # loop through weather functions at designated elapsed time intervals
        if (success == True and elapsedTime >= TIME_BETWEEN_CALLS) or (success == False and elapsedTime >= TIME_BETWEEN_FAILED) or (boot == True and elapsedTime >= TIME_WAIT_STARTUP):
            try:
                # attempt to fetch weather data
                writeLogFile('\n\n-----Connecting-----', 'a')
                writeLogFile('\n\n' + str(apiUrl), 'a')
                writeLogFile('\n\nWeather data provided by The Weather Underground, LLC (WUL)', 'a')
                response = urlopen(apiUrl).read().decode('utf8')
            except:
                # handle failed api call
                # utilizes red color wipe to signal api call failed at boot
                if boot == True:
                    colorWipe(strip, Color(0,255,0))
                boot = False
                success = False
                loopCount += 1
                startTime = time.time()
                writeLogFile('\n\nFailed to connect to API. Trying again in ' + str(TIME_BETWEEN_FAILED) + ' seconds.', 'a')
            else:
                # continue after successful api call
                boot = False
                success = True
                loopCount += 1
                startTime = time.time()
                obj = json.loads(response)
                # call function to parse weather data
                writeLogFile('\n\n-----Parsing-----', 'a')
                tempData, pressData, humidData, precipData, windData, fctData, fctTime = parseWeatherData(obj)
                # call function to assign color values to weather data
                writeLogFile('\n\n-----Coloring-----', 'a')
                tempColor, pressColor, humidColor, precipColor, windColor, fctColor = colorAssign(tempData, pressData, humidData, precipData, windData, fctData)
                # display weather data
                writeLogFile('\n\n******** Weather Loop Number ' + str(loopCount) + ' ********', 'a')
                writeLogFile('\n\nTemperature Data: ' + str(tempData) + '\nTemperature Color: ' + str(tempColor), 'a')
                writeLogFile('\n\nPressure Data: ' + str(pressData) + '\nPressure Color: ' + str(pressColor), 'a')
                writeLogFile('\n\nHumidity Data: ' + str(humidData) + '\nHumidity Color: ' + str(humidColor), 'a')
                writeLogFile('\n\nWind Data: ' + str(windData) + '\nWind Color: ' + str(windColor), 'a')
                writeLogFile('\n\nPrecipitation Data: ' + str(precipData) + '\nPrecipitation Color: ' + str(precipColor), 'a')
                writeLogFile('\n\nForecast Data: ' + str(fctData) + '\nForecast Color: ' + str(fctColor), 'a')
                writeLogFile('\n\nForecast Time: ' + str(fctTime), 'a')
                # call functions to push weather data to each LED strip
                colorSet(strip, tempColor, 0)
                colorSet(strip, pressColor, 1*STRIP_COUNT)
                colorSet(strip, humidColor, 2*STRIP_COUNT)
                colorSet(strip, windColor, 3*STRIP_COUNT)
                colorSet(strip, precipColor, 4*STRIP_COUNT)
                colorSet(strip, fctColor, 5*STRIP_COUNT)
                # use the sleep function as a delay to save cpu cycles when counting elapsed time 
                time.sleep(TIME_BETWEEN_CALLS)
        elapsedTime = time.time() - startTime

main()
