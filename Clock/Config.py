# -*- coding: utf-8 -*-
from PyQt5.QtGui import QColor
from GoogleMercatorProjection import LatLng

# LOCATION(S)
# Further radar configuration (zoom, marker location) can be
# completed under the RADAR section
primary_coordinates = 69.008538, 33.089840  # Change to your Lat/Lon

location = LatLng(primary_coordinates[0], primary_coordinates[1])
primary_location = LatLng(primary_coordinates[0], primary_coordinates[1])
#noaastream = 'http://www.urberg.net:8000/tim273/edina'
noaastream = 'http://www.meteonova.ru/speech/forecast_33990_0.mp3'

background = 'images/dark.png'
squares1 = 'images/squares1-kevin.png'
squares2 = 'images/squares2-kevin.png'
#icons = 'icons-climacell'  # иконки для climacell.io
#icons = 'icons-lightblue'
icons = 'icons-weatherapi'

textcolor = '#ffe4e1'   
clockface = 'images/myclockface3.png'
hourhand = 'images/myhour.png'
minhand = 'images/mymin.png'
sechand = 'images/mysechand.png'

textcolorTopLine = '#20FFFF'     #Цвет верхняя строка
textcolorDatex2 = '#20FFFF'  # Цвет строка день недели на второй странице
textcolorDatey2 = 'yellow' # Цвет время на второй странице
textcolorWeather = '#FFB520' # Строка состояние погоды слева вверху
textcolorWeather2 = '#FF6800' # Строка состояние погоды на второй странице 
textcolorTemper = 'white' # Цвет Температура вверху слева
textcolorTemper2 = 'white' # Цвет Температура на второй странице

textcolorPress = '#3774FF' # Строка Давление слева
textcolorHumidity = '#FF8520'# '#ff0000' # Цвет строка Влажность

colorCCfields = '#C93C20'  # цвет строки Видимость, Облачность, УФ индекс
textcolorTempInDoor = '#7366BD' # Цвет Температура В помещении
textcolorBottom = '#9ACD32' # Цвет нижняя строка Восх, Зах, Луна
textcolorDayWeek = "#day { background-color: transparent; color:#66ff00}"#  Цинково-жёлтый '#ffa500'# Цвет Дней недели справа 1-9

fontmult = 1  # коэф. размера шрифта

sensds18b20 = '020d9177addb'  # серийный номер Датчика температуры ds18b20 без '28-'. Комманда для проверки: ls -l /sys/bus/w1/devices 

# sensor thingspeak.com
ChannelID = "1587023"  # Channel ID:
Field = "4"  # Field#

# SlideShow
useslideshow = 0  # 1 to enable, 0 to disable
slide_time = 305  # in seconds, 3600 per hour
slides = 'images/slideshow'  # the path to your local images
slide_bg_color = "#000"  # https://htmlcolorcodes.com/  black #000

digital = 0  # 1 = Digital Clock, 0 = Analog Clock

# Goes with light blue config (like the default one)
digitalcolor = "#50CBEB"
digitalformat = "{0:%I:%M\n%S %p}"  # Format of the digital clock face
digitalsize = 200

# The above example shows in this way:
#  https://github.com/n0bel/PiClock/blob/master/Documentation/Digital%20Clock%20v1.jpg
# (specifications of the time string are documented here:
#  https://docs.python.org/2/library/time.html#time.strftime)

# digitalformat = "{0:%I:%M}"
# digitalsize = 250
# The above example shows in this way:
# https://github.com/n0bel/PiClock/blob/master/Documentation/Digital%20Clock%20v2.jpg

digitalformat2 = "{0:%H:%M:%S}"  # Format of the digital time on second screen

usemapbox = 1  # Use Mapbox.com for maps, needs api key (mbapi in ApiKeys.py)

#map_base = 'bcurley/cj712peyz0bwr2sqfndbggupb'  # Custom dark Mapbox style for land and water only (bottom layer that goes below weather radar)
map_overlay = 'bcurley/cj712r01c0bw62rm9isme3j8c'  # Custom Mapbox style for labels, roads, and borders only (top layer that goes above weather radar)

map_base = 'mapbox/satellite-streets-v11' # Uncomment for standard Mapbox style, and comment/remove the custom style
#map_overlay = '' # Uncomment and leave blank for standard Mapbox style, and comment/remove the custom style

# Sign-in and create custom map styles at https://studio.mapbox.com/
# Example: If static map URL is
# https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/-80.2,25.8,10/600x400?access_token=YOUR-ACCESS-TOKEN
# use the portion between '/styles/v1/' and '/static/'
# Standard Mapbox maps will look like 'mapbox/streets-v11'
# User created Mapbox maps will look like 'user-name/map-identifier'

metric = 1  # 0 = English, 1 = Metric
radar_refresh = 10  # minutes
weather_refresh = 30  # minutes
# Wind in degrees instead of cardinal 0 = cardinal(направление, откуда дует ветер), 1 = degrees(градусы)
wind_degrees = 0

# gives all text additional attributes using QT style notation
# example: fontattr = 'font-weight: bold; '
#fontattr = ''

#толщина шрифта font-weight: (100-900);font-style: ( normal, italic, oblique)
fontattr = 'font-weight: 900; font-style: italic' #

# These are to dim the radar images, if needed.
# see and try Config-Example-Bedside.py
dimcolor = QColor('#000000')
dimcolor.setAlpha(0)

# Optional Current conditions replaced with observations from a METAR station
# METAR is world wide, provided mostly for pilots
# But data can be sparse outside US and Europe
# If you're close to an international airport, you should find something close
# Find the closest METAR station with the following URL
# https://www.aviationweather.gov/metar
# scroll/zoom the map to find your closest station
# or look up the ICAO code here:
# https://airportcodes.aero/name

#METAR = ''

# Language Specific wording
# DarkSky Language code
# (https://darksky.net/dev/docs under lang=)
# и для openweahermap.org
Language = "ru" 

# The Python Locale for date/time (locale.setlocale)
#  '' for default Pi Setting
# Locales must be installed in your Pi.. to check what is installed
# locale -a
# to install locales
# sudo dpkg-reconfigure locales
DateLocale = 'ru_RU.UTF-8'
# Language specific wording
LPressure = u"Давление: "
LHumidity = u"Влажн: "
LWind = u"Ветер: "
Lgusting = u" порывы: "
LFeelslike = u"по Ощущению: "
LPrecip1hr = u" Осадки 1hr:"
LToday = u"Сегодня: "
LSunRise = u"Восх "
LSet = u" Зах "
LMoonPhase = u" "
LInsideTemp = u"В помещении: "
LOutsideTemp = u"На улице: "
LRain = u" Дождь: "

Lvisibility = u'Видимость: '
LcloudCover = u'Облачность: '
LuvIndex = u'УФ индекс: '

LSnow = u" Снег: "
Lmoon1 = u'Новолуние'
Lmoon2 = u'Молодая луна'
Lmoon3 = u'Луна в Первой четверти'
Lmoon4 = u'Прибывающая луна'
Lmoon5 = u'Полнолуние'
Lmoon6 = u'Убывающая луна'
Lmoon7 = u'Луна в посл четв'
Lmoon8 = u'Старая луна'
# Language Specific terms for weather conditions


Lcc_code_map = {
    0: "Unknown",
    1000: u"Ясно",
    1100: u"Малооблачно",
    1101: u"Переменная облачность",
    1102: u"Облачно с прояснениями",
    1001: u"Облачно",
    2000: u"Туман",
    2100: u"Слабый туман",
    4000: u"Морось",
    4001: u"Дождь",
    4200: u"Небольшой дождь",
    4201: u"Ливень",
    5000: u"Снег",
    5001: u"Небольшой снег",
    5100: u"Слабый снег",
    5101: u"Сильный снег",
    6000: u"Изморозь",
    6001: u"Ледяной дождь",
    6200: u"Ледяная морось",
    6201: u"Сильный Ледяной дождь",
    7000: u"Ледяная крупа",
    7101: u"Сильный Град",
    7102: u"Небольшая ледяная крупа",
    8000: u"Гроза"
}


# RADAR
# By default, primary_location entered will be the
#  center and marker of all radar images.
# To update centers/markers, change radar sections
# below the desired lat/lon as:
# -FROM-
# primary_location,
# -TO-
# LatLng(44.9764016,-93.2486732),
radar1 = {
    'center': primary_location,  # the center of your radar block
    'zoom': 7,  # this is a maps zoom factor, bigger = smaller area
    'basemap': map_base,  # Mapbox style for standard map or custom map with land and water only
    'overlay': map_overlay,  # Mapbox style for labels, roads, and borders only
    'color': 6,  # rainviewer radar color style:
    # https://www.rainviewer.com/api.html#colorSchemes
    'smooth': 1,  # rainviewer radar smoothing
    'snow': 1,  # rainviewer radar show snow as different color
    'markers': (  # google maps markers can be overlaid
        {
            'visible': 1,  # 0 = hide marker, 1 = show marker
            'location': primary_location,
            'color': 'red',
            'size': 'small',
            'image': 'teardrop-dot',  # optional image from the markers folder
        },  # dangling comma is on purpose.
    )
}

radar2 = {
    'center': primary_location,
    'zoom': 11,
    'basemap': map_base,
    'overlay': map_overlay,
    'color': 6,
    'smooth': 1,
    'snow': 1,
    'markers': (
        {
            'visible': 1,
            'location': primary_location,
            'color': 'red',
            'size': 'small',
            'image': 'teardrop-dot',
        },
    )
}

radar3 = {
    'center': primary_location,
    'zoom': 7,
    'basemap': map_base,
    'overlay': map_overlay,
    'color': 6,
    'smooth': 1,
    'snow': 1,
    'markers': (
        {
            'visible': 1,
            'location': primary_location,
            'color': 'red',
            'size': 'small',
            'image': 'teardrop-dot',
        },
    )
}

radar4 = {
    'center': primary_location,
    'zoom': 11,
    'basemap': map_base,
    'overlay': map_overlay,
    'color': 6,
    'smooth': 1,
    'snow': 1,
    'markers': (
        {
            'visible': 1,
            'location': primary_location,
            'color': 'red',
            'size': 'small',
            'image': 'teardrop-dot',
        },
    )
}
