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
# A tutorial for the complete project can be found at http://www.instructables.com/id/LED-Weather-Forecast. The basic hardware 
# and software setup can be found at https://learn.adafruit.com/neopixels-on-raspberry-pi. The NeoPixel library for the Raspberry 
# Pi (rpi_ws281x library) can be found at https://github.com/jgarff. The weather data and API are provided by Weather Underground, 
# LLC (WUL). An API key can be obtained at www.wunderground.com/weather/api.

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
LED_BRIGHTNESS = 7                 # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False              # True to invert the signal (when using NPN transistor level shift)

# other constants
OBJMAX = 32                         # set max number of objects to parse from weather data
HOURMULT = 2                        # set multiplier for LED hour representation
RMULT = 1                           # multiplier to adjust for red LED brightness
GMULT = .8                          # multiplier to adjust for green LED brightness
BMULT = .8                          # multiplier to adjust for blue LED brightness
COLORVAL = 10                       # set max number for color array
PATH_NAME = "//home//pi//weather_color//"  # set path to find apiboot.txt and log.txt files
TEMPMIN = 0                         # minimum value for normalized temperature range
TEMPMAX = 100                       # maximum value for normalized temperature range
TEMPDELTA = TEMPMAX - TEMPMIN       # delta value for normalized temperature range
PRESSMIN = 28.8                     # minimum value for normalized pressure range
PRESSMAX = 31.1                     # maximum value for normalized pressure range
PRESSDELTA = PRESSMAX - PRESSMIN    # delta value for normalized pressure range
HUMIDMIN = 0                        # minimum value for normalized humidity range
HUMIDMAX = 100                      # maximum value for normalized humidity range
HUMIDDELTA = HUMIDMAX - HUMIDMIN    # delta value for normalized humidity range
PRECIPMIN = 0                       # minimum value for normalized precipitation range
PRECIPMAX = 100                     # maximum value for normalized precipitation range
PRECIPDELTA = PRECIPMAX - PRECIPMIN # delta value for normalized precipitation range
WINDMIN = 0                         # minimum value for normalized wind speed range
WINDMAX = 45                        # maximum value for normalized wind speed range
WINDDELTA = WINDMAX - WINDMIN       # delta value for normalized wind speed range
TIME_BETWEEN_CALLS = 900            # time in seconds between calls to the weather api
TIME_BETWEEN_FAILED = 300           # time in seconds between failed calls to the weather api
RAINBOW_BOOT_ITERATIONS = 15        # set iterations to correspond to Pi boot time and ensure wifi connectivity
MAX_FAIL_LOOP_COUNT = 15            # maximum number of attempts to retrieve data from API before program terminates

def readApiBootFile():
    # opens apiboot.txt file and reads the api key (obtain from weather underground) and one uncommented query line
    # this function ignores the '#' in the file for comments
    i = 0
    a = [None]*2
    textFile = open(PATH_NAME + "apiboot.txt", "r")
    while i < 2:
        a[i] = textFile.readline().rstrip('\n')
        if a[i][0] != "#":
            i += 1
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

def rainbow(strip, wait_ms=10, iterations=RAINBOW_BOOT_ITERATIONS):
    # draw rainbow that fades across all pixels at once
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

def parseWeatherData(strip, obj):
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
    offsetA = 1.0                          # offset value used to help persuade normalized colors
    offsetB = 2.5                          # offset value used to help persuade normalized colors
    blue = 2                               # RGB blue truncate value
    
    for i in range(OBJMAX):
        # normalize color values for temperature data
        if temp[i] <= TEMPMIN:
            tempClr[i] = 0
        elif temp[i] >= TEMPMAX:
            tempClr[i] = COLORVAL
        else:
            tempClr[i] = int(offsetA + (COLORVAL - offsetA)*((temp[i] - TEMPMIN)/(TEMPDELTA)))
        
        # normalize color values for pressure data
        if press[i] <= PRESSMIN:
            pressClr[i] = 0
        elif press[i] >= PRESSMAX:
            pressClr[i] = COLORVAL
        else:
            pressClr[i] = int(offsetA + (COLORVAL - offsetA)*((press[i] - PRESSMIN)/(PRESSDELTA)))
            
        # normalize color values for humidity data - except truncate low values to RGB blue
        if humid[i] <= HUMIDMIN:
            humidClr[i] = blue
        elif humid[i] >= HUMIDMAX:
            humidClr[i] = COLORVAL
        else:
            humidClr[i] = int(offsetB + (COLORVAL - offsetB)*((humid[i] - HUMIDMIN)/(HUMIDDELTA)))

        # normalize color values for precipation data - except truncate low values to RGB blue
        if precip[i] <= PRECIPMIN:
            precipClr[i] = blue
        elif precip[i] >= PRECIPMAX:
            precipClr[i] = COLORVAL
        else:
            precipClr[i] = int(offsetB + (COLORVAL - offsetB)*((precip[i] - PRECIPMIN)/(PRECIPDELTA)))

        # normalize color values for wind speed data - except truncate low values to RGB blue
        if wind[i] <= WINDMIN:
            windClr[i] = blue
        elif wind[i] >= WINDMAX:
            windClr[i] = COLORVAL
        else:
            windClr[i] = int(offsetB + (COLORVAL - offsetB)*((wind[i] - WINDMIN)/(WINDDELTA)))

        # assign color values to forecast codes
        if fct[i] == 1:
            fctClr[i] = 6
        elif fct[i] == 2:
            fctClr[i] = 5
        elif fct[i] == 3:
            fctClr[i] = 4
        elif fct[i] == 4 or fct[i] == 5 or fct[i] == 6 or fct[i] == 18 or fct[i] == 20:
            fctClr[i] = 3
        elif fct[i] == 16:
            fctClr[i] = 2
        elif fct[i] == 10 or fct[i] == 12:
            fctClr[i] = 8
        elif fct[i] == 7 or fct[i] == 11 or fct[i] == 13:
            fctClr[i] = 9
        elif fct[i] == 14 or fct[i] == 15 or fct[i] == 24:
            fctClr[i] = 10
        elif fct[i] == 19 or fct[i] == 21:
            fctClr[i] = 1
        elif fct[i] == 8 or fct[i] == 9 or fct[i] == 22 or fct[i] == 23:
            fctClr[i] = 0
        else:
            fctClr[i] = 6
            
    return tempClr, pressClr, humidClr, precipClr, windClr, fctClr

def fetchWeatherData(strip):
    success = False
    failedLoopCount = 0
    error = 'foo'
    
    try:
        # fetch API key and query values from boot file
        apiVal = readApiBootFile()
    except:
        # utilize red color wipe to signal failed boot file read
        writeLogFile("\n\nFailed to read apiboot.txt file. Terminating Program.\nCheck that file exists.\nCheck that the file contains your API key.\nCheck that the file has at least one query line uncommented.", "a")
        colorWipe(strip, Color(0,255,0))
        raise SystemExit('failed to read apiboot file')
    else:
        apiUrl = "http://api.wunderground.com/api/" + str(apiVal[0]) + "/hourly/q/" + str(apiVal[1]) + ".json"
    
    while success == False:  
        try:
            # check for internet connection using common url
            response = urlopen('https://www.google.com/').read()
            success = True
        except:
            # utilize yellow color wipe to signal error and increment failed loop count
            success = False
            failedLoopCount += 1
            writeLogFile('\n\nFailed to connect to internet after attempt ' + str(failedLoopCount) + '.', 'a')
            writeLogFile('\nProgram will terminate after ' + str(MAX_FAIL_LOOP_COUNT) + ' consecutive attempts.', 'a')
            writeLogFile('\nTrying again in ' + str(TIME_BETWEEN_FAILED) + ' seconds.', 'a')
            colorWipe(strip, Color(255,255,0))

        if success == True:            
            try:
                # attempt to fetch weather data
                writeLogFile('\n\n' + str(apiUrl), 'a')
                writeLogFile('\n\nWeather data provided by The Weather Underground, LLC (WUL)', 'a')
                response = urlopen(apiUrl).read().decode('utf8')
                obj = json.loads(response)
                success = True
            except:
                # utilize yellow color wipe to signal error and increment failed loop count
                success = False
                failedLoopCount += 1
                writeLogFile('\n\nFailed to connect to API after attempt ' + str(failedLoopCount) + '.', 'a')
                writeLogFile('\nProgram will terminate after ' + str(MAX_FAIL_LOOP_COUNT) + ' consecutive attempts.', 'a')
                writeLogFile('\nTrying again in ' + str(TIME_BETWEEN_FAILED) + ' seconds.', 'a')
                colorWipe(strip, Color(255,255,0))

        if success == True:
            try:
                # verify that API returned no errors
                error = str(obj["response"]["error"]["type"])
            except:
                success = True
            else:
                # utilize red color wipe to signal error from api
                writeLogFile('\n\nReceived an error response from the API: ' + error + '. Terminating program.','a')
                colorWipe(strip, Color(0,255,0))
                raise SystemExit('some error from api')

        if success == True:
            try:
                # verify that API returned hourly forecast data
                error = str(obj["hourly_forecast"][0]["temp"]["english"])
                success = True
            except:
                # utilize yellow color wipe to signal error and increment failed loop count
                success = False
                failedLoopCount += 1
                writeLogFile('\n\nAPI failed to provide forecast data after attempt ' + str(failedLoopCount) + '.', 'a')
                writeLogFile('\nProgram will terminate after ' + str(MAX_FAIL_LOOP_COUNT) + ' consecutive attempts.', 'a')
                writeLogFile('\nTrying again in ' + str(TIME_BETWEEN_FAILED) + ' seconds.', 'a')
                colorWipe(strip, Color(255,255,0))                

        if failedLoopCount > MAX_FAIL_LOOP_COUNT:
            writeLogFile('\n\nTerminating program after ' + str(MAX_FAIL_LOOP_COUNT) + ' attempts to retrieve data from API.','a')
            colorWipe(strip, Color(0,255,0))
            raise SystemExit('failed to retrieve data after multiple attempts')
            
        if success == False:
            time.sleep(TIME_BETWEEN_FAILED)
            
    return(obj)

def main():
    # Create NeoPixel object with appropriate configuration.
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
    
    # Intialize the library (must be called once before other functions).
    strip.begin()
    
    # demonstrate LED strip with rainbow cycle during Pi startup
    writeLogFile('-----Demonstrate Rainbow Chase-----', 'w')
    rainbow(strip)
    
    # main routine to fetch, parse, and color weather data
    while True:
        # call function to fetch weather data - function will terminate if bad or no data is returned
        writeLogFile('-----Attempting to Fetch Data-----', 'w')
        obj = fetchWeatherData(strip)
        writeLogFile('\n\n' + str(obj),'a')
        
        # call function to parse weather data
        writeLogFile('\n\n-----Parsing-----', 'a')
        tempData, pressData, humidData, precipData, windData, fctData, fctTime = parseWeatherData(strip, obj)

        # call function to assign color values to weather data
        writeLogFile('\n\n-----Coloring-----', 'a')
        tempColor, pressColor, humidColor, precipColor, windColor, fctColor = colorAssign(tempData, pressData, humidData, precipData, windData, fctData)
        
        # display weather data
        writeLogFile('\n\n-----Results-----', 'a')
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

main()
