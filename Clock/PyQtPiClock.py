#!/usr/bin/env python3                        # Climacell
# -*- coding: utf-8 -*-

import requests
import datetime
import json
import locale
import math
import os
import platform
import random
import signal
import sys
import time
from subprocess import Popen

from w1thermsensor import W1ThermSensor, Sensor
import dateutil.parser #date/time string parser 
import tzlocal
from PyQt5 import QtGui, QtCore, QtNetwork, QtWidgets
from PyQt5.QtCore import QUrl
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QImage, QFont
from PyQt5.QtGui import QPixmap, QBrush, QColor
from PyQt5.QtNetwork import QNetworkReply
from PyQt5.QtNetwork import QNetworkRequest

sys.dont_write_bytecode = True
from GoogleMercatorProjection import get_corners, get_point, get_tile_xy, LatLng  # NOQA
import ApiKeys  # NOQA


class TimeZoneUTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=0, minutes=0)


class SunTimes:
    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng

    def sunrise(self, when=None):
        if when is None:
            when = datetime.datetime.now(tz=tzlocal.get_localzone())
        self.__preptime(when)
        self.__calc()
        return SunTimes.__timefromdecimalday(self.sunrise_t)

    def sunset(self, when=None):
        if when is None:
            when = datetime.datetime.now(tz=tzlocal.get_localzone())
        self.__preptime(when)
        self.__calc()
        return SunTimes.__timefromdecimalday(self.sunset_t)

    @staticmethod
    def __timefromdecimalday(day):
        hours = 24.0 * day
        h = int(hours)
        minutes = (hours - h) * 60
        m = int(minutes)
        seconds = (minutes - m) * 60
        s = int(seconds)
        return datetime.time(hour=h, minute=m, second=s)

    def __preptime(self, when):
        # datetime days are numbered in the Gregorian calendar
        # while the calculations from NOAA are distributed as
        # OpenOffice spreadsheets with days numbered from
        # 1/1/1900. The difference are those numbers taken for
        # 18/12/2010
        self.day = when.toordinal() - (734124 - 40529)
        t = when.time()
        self.time = (t.hour + t.minute / 60.0 + t.second / 3600.0) / 24.0

        self.timezone = 0
        offset = when.utcoffset()
        if offset is not None:
            self.timezone = offset.seconds / 3600.0 + (offset.days * 24)

    def __calc(self):
        timezone = self.timezone  # in hours, east is positive
        longitude = self.lng  # in decimal degrees, east is positive
        latitude = self.lat  # in decimal degrees, north is positive

        time = self.time  # percentage past midnight, i.e. noon  is 0.5
        day = self.day  # daynumber 1=1/1/1900

        j_day = day + 2415018.5 + time - timezone / 24  # Julian day
        j_cent = (j_day - 2451545) / 36525  # Julian century

        m_anon = 357.52911 + j_cent * (35999.05029 - 0.0001537 * j_cent)
        m_long = 280.46646 + j_cent * (36000.76983 + j_cent * 0.0003032) % 360
        eccent = 0.016708634 - j_cent * (0.000042037 + 0.0001537 * j_cent)
        m_obliq = (23 + (26 + ((21.448 - j_cent * (46.815 + j_cent *
                                                   (0.00059 - j_cent * 0.001813)))) / 60) / 60)
        obliq = (m_obliq + 0.00256 *
                 math.cos(math.radians(125.04 - 1934.136 * j_cent)))
        vary = (math.tan(math.radians(obliq / 2)) *
                math.tan(math.radians(obliq / 2)))
        s_eqcent = (math.sin(math.radians(m_anon)) *
                    (1.914602 - j_cent * (0.004817 + 0.000014 * j_cent)) +
                    math.sin(math.radians(2 * m_anon))
                    * (0.019993 - 0.000101 * j_cent) +
                    math.sin(math.radians(3 * m_anon)) * 0.000289)
        s_truelong = m_long + s_eqcent
        s_applong = (s_truelong - 0.00569 - 0.00478 *
                     math.sin(math.radians(125.04 - 1934.136 * j_cent)))
        declination = (math.degrees(math.asin(math.sin(math.radians(obliq)) *
                                              math.sin(math.radians(s_applong)))))

        eqtime = (4 * math.degrees(vary * math.sin(2 * math.radians(m_long)) -
                                   2 * eccent * math.sin(math.radians(m_anon)) + 4 * eccent *
                                   vary * math.sin(math.radians(m_anon)) *
                                   math.cos(2 * math.radians(m_long)) - 0.5 * vary * vary *
                                   math.sin(4 * math.radians(m_long)) - 1.25 * eccent * eccent *
                                   math.sin(2 * math.radians(m_anon))))

        hourangle0 = (math.cos(math.radians(90.833)) /
                      (math.cos(math.radians(latitude)) *
                       math.cos(math.radians(declination))) -
                      math.tan(math.radians(latitude)) *
                      math.tan(math.radians(declination)))

        self.solarnoon_t = (720 - 4 * longitude - eqtime + timezone * 60) / 1440
        # sun never sets
        if hourangle0 > 1.0:
            self.sunrise_t = 0.0
            self.sunset_t = 1.0 - 1.0 / 86400.0
            return
        if hourangle0 < -1.0:
            self.sunrise_t = 0.0
            self.sunset_t = 0.0
            return

        hourangle = math.degrees(math.acos(hourangle0))

        self.sunrise_t = self.solarnoon_t - hourangle * 4 / 1440
        self.sunset_t = self.solarnoon_t + hourangle * 4 / 1440


# https://gist.github.com/miklb/ed145757971096565723
def moon_phase(dt=None):
    if dt is None:
        dt = datetime.datetime.now()
    diff = dt - datetime.datetime(2001, 1, 1)
    days = float(diff.days) + (float(diff.seconds) / 86400.0)
    lunations = 0.20439731 + float(days) * 0.03386319269
    return lunations % 1.0


def tick():
    global hourpixmap, minpixmap, secpixmap
    global hourpixmap2, minpixmap2, secpixmap2
    global lastmin, lastday, lasttimestr
    global clockrect
    global datex, datex2, datey2, pdy
    global sun, daytime, sunrise, sunset
    global bottom

    if Config.DateLocale != "":
        try:
            locale.setlocale(locale.LC_TIME, Config.DateLocale)
        except AttributeError:
            pass

    now = datetime.datetime.now()
    if Config.digital:
        timestr = Config.digitalformat.format(now)
        if Config.digitalformat.find("%I") > -1:
            if timestr[0] == '0':
                timestr = timestr[1:99]
        if lasttimestr != timestr:
            clockface.setText(timestr.lower())
        lasttimestr = timestr
    else:
        angle = now.second * 6
        ts = secpixmap.size()
        secpixmap2 = secpixmap.transformed(
            QtGui.QTransform().scale(
                float(clockrect.width()) / ts.height(),
                float(clockrect.height()) / ts.height()
            ).rotate(angle),
            Qt.SmoothTransformation
        )
        sechand.setPixmap(secpixmap2)
        ts = secpixmap2.size()
        sechand.setGeometry(
            int(clockrect.center().x() - ts.width() / 2),
            int(clockrect.center().y() - ts.height() / 2),
            ts.width(),
            ts.height()
        )
        if now.minute != lastmin:
            angle = now.minute * 6
            ts = minpixmap.size()
            minpixmap2 = minpixmap.transformed(
                QtGui.QTransform().scale(
                    float(clockrect.width()) / ts.height(),
                    float(clockrect.height()) / ts.height()
                ).rotate(angle),
                Qt.SmoothTransformation
            )
            minhand.setPixmap(minpixmap2)
            ts = minpixmap2.size()
            minhand.setGeometry(
                int(clockrect.center().x() - ts.width() / 2),
                int(clockrect.center().y() - ts.height() / 2),
                ts.width(),
                ts.height()
            )

            angle = ((now.hour % 12) + now.minute / 60.0) * 30.0
            ts = hourpixmap.size()
            hourpixmap2 = hourpixmap.transformed(
                QtGui.QTransform().scale(
                    float(clockrect.width()) / ts.height(),
                    float(clockrect.height()) / ts.height()
                ).rotate(angle),
                Qt.SmoothTransformation
            )
            hourhand.setPixmap(hourpixmap2)
            ts = hourpixmap2.size()
            hourhand.setGeometry(
                int(clockrect.center().x() - ts.width() / 2),
                int(clockrect.center().y() - ts.height() / 2),
                ts.width(),
                ts.height()
            )

    dy = "{0:%H:%M}".format(now)  #                       Время на второй странице
    if Config.digitalformat2.find("%I") > -1:
        if dy[0] == '0':
            dy = dy[1:99]
    if dy != pdy:
        pdy = dy
        datey2.setText(dy)

    if now.minute != lastmin:
        lastmin = now.minute
        if sunrise <= now.time() <= sunset:
            daytime = True
        else:
            daytime = False

    if now.day != lastday:
        lastday = now.day

# date
        sup = 'th'
        if now.day == 1 or now.day == 21 or now.day == 31:
            sup = 'st'
        if now.day == 2 or now.day == 22:
            sup = 'nd'
        if now.day == 3 or now.day == 23:
            sup = 'rd'
        if Config.DateLocale != "":
            sup = ""        
        weekday = "{0:%w}".format(now)
        if (weekday == '0'):
            weekrus = u' Воскресенье '
        if (weekday == '1'):
            weekrus = u' Понедельник '
        if (weekday == '2'):
            weekrus = u' Вторник '
        if (weekday == '3'):
            weekrus = u' Среда '
        if (weekday == '4'):
            weekrus = u' Четверг '
        if (weekday == '5'):
            weekrus = u' Пятница '
        if (weekday == '6'):
            weekrus = u' Суббота '
        month = "{0:%m}".format(now)
        monthrus = ''
        if (month == '01'):
            monthrus = u'Января'
        if (month == '02'):
            monthrus = u'Февраля'
        if (month == '03'):
            monthrus = u'Марта'
        if (month == '04'):
            monthrus = u'Апреля'
        if (month == '05'):
            monthrus = u'Мая'
        if (month == '06'):
            monthrus = u'Июня'
        if (month == '07'):
            monthrus = u'Июля'
        if (month == '08'):
            monthrus = u'Августа'
        if (month == '09'):
            monthrus = u'Сентября'
        if (month == '10'):
            monthrus = u'Октября'
        if (month == '11'):
            monthrus = u'Ноября'
        if (month == '12'):
            monthrus = u'Декабря'

        ds = u" {1} {0:%d} {2} {0.year}г. ".format(now, weekrus, monthrus) #  ДАТА сверху
        datex.setText(ds)
        datex2.setText(ds)
        ds2 = u" {0:%d} {2} {0.year}г. ".format(now, weekrus, monthrus) #     ДАТА на второй странице

        datex.setText(ds)
        datex2.setText(ds2)
        dt = datetime.datetime.now(tz=tzlocal.get_localzone())
        sunrise = sun.sunrise(dt)
        sunset = sun.sunset(dt)
        bottomtext = ""
        bottomtext += (Config.LSunRise +
                       "{0:%H:%M}".format(sunrise) + ',' +
                       Config.LSet +
                       "{0:%H:%M}".format(sunset) + ',')  #           Запятая Восх Зах   
        bottomtext += (Config.LMoonPhase + phase(moon_phase()))
        bottom.setText(bottomtext)


def tempfinished():
#    global tempreply, temp
    global temp

# sensor ds18b20 
    sensor = W1ThermSensor(Sensor.DS18B20, Config.sensds18b20)
    tempdata = sensor.get_temperature()
# sensor thingspeak.com
    url = "https://api.thingspeak.com/channels/" + Config.ChannelID + "/fields/" + Config.Field + ".json?api_key=" + ApiKeys.tsApiKey + "&results=1"
    response = requests.get(url)
    data_disc = json.loads(response.text) 
    flt = float(data_disc['feeds'][0]['field4'])

    if Config.metric:
        s = Config.LInsideTemp + str('%.1f' % tempdata) + u'°C   ' + Config.LOutsideTemp +  \
                str('%.1f' % flt) + u'°C'                   #                       Температура внутри и на улице

    else:
        s = Config.LInsideTemp + str('%.1f' % (tempdata * 1.8 + 32)) + u'°F   ' + Config.LOutsideTemp +  \
                str('%.1f' % (flt * 1.8 + 32)) + u'°F'   
       
    temp.setText(s)


def tempm(f):
    return (f - 32) / 1.8


def speedm(f):
    return f * 0.44704 # m/sec


def pressi(f):
    return f  * 0.029530


def heightm(f):
    return f * 25.4


def barom(f):
    return f * 25.4



def phase(f):
    pp = Config.Lmoon1  # 'New Moon'
    if f > 0.9375:
        pp = Config.Lmoon1  # 'New Moon'
    elif f > 0.8125:
        pp = Config.Lmoon8  # 'Waning Crescent'
    elif f > 0.6875:
        pp = Config.Lmoon7  # 'Third Quarter'
    elif f > 0.5625:
        pp = Config.Lmoon6  # 'Waning Gibbous'
    elif f > 0.4375:
        pp = Config.Lmoon5  # 'Full Moon'
    elif f > 0.3125:
        pp = Config.Lmoon4  # 'Waxing Gibbous'
    elif f > 0.1875:
        pp = Config.Lmoon3  # 'First Quarter'
    elif f > 0.0625:
        pp = Config.Lmoon2  # 'Waxing Crescent'
    return pp


def bearing(f):
    wd = u'С'
    if (f > 22.5):
        wd = u'СВ, '
    if (f > 67.5):
        wd = u'В, '
    if (f > 112.5):
        wd = u'ЮВ, '
    if (f > 157.5):
        wd = u'Ю, '
    if (f > 202.5):
        wd = u'ЮЗ, '
    if (f > 247.5):
        wd = u'З, '
    if (f > 292.5):
        wd = u'СЗ, '
    if (f > 337.5):
        wd = u'С, '
    return wd


def gettemp():
    global tempreply
    host = 'localhost'
#    if platform.uname()[1] == 'KW81':
#        host = 'piclock.local'  # this is here just for testing
    r = QUrl('http://' + host + ':48213/temp')
    r = QNetworkRequest(r)
    tempreply = manager.get(r)
    tempreply.finished.connect(tempfinished)

def wxfinished_owm():
    global wxreply, wxdata, supress_current
    global wxicon, temper, wxdesc, press, humidity, ccfields
    global wind, feelslike, wdate, bottom, forecast
    global wxicon2, temper2, wxdesc2, attribution
    global daytime
    owmicons = {
        '01d': 'clear-day',
        '02d': 'partly-cloudy-day',
        '03d': 'partly-cloudy-day',
        '04d': 'partly-cloudy-day',
        '09d': 'rain',
        '10d': 'rain',
        '11d': 'thunderstorm',
        '13d': 'snow',
        '50d': 'fog',
        '01n': 'clear-night',
        '02n': 'partly-cloudy-night',
        '03n': 'partly-cloudy-night',
        '04n': 'partly-cloudy-night',
        '09n': 'rain',
        '10n': 'rain',
        '11n': 'thunderstorm',
        '13n': 'snow',
        '50n': 'fog'
    }
    attribution.setText("OpenWeatherMap.org")
    attribution2.setText("OpenWeatherMap.org")

    wxstr = str(wxreply.readAll(), 'utf-8')
    wxdata = json.loads(wxstr)
    f = wxdata['current']
#    print(wxdata)    
    icon = f['weather'][0]['icon']
    icon = owmicons[icon]


    if not supress_current:
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + icon + ".png")
        wxicon.setPixmap(wxiconpixmap.scaled(
            wxicon.width(), wxicon.height(), Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wxicon2.setPixmap(wxiconpixmap.scaled(
            wxicon.width(),
            wxicon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wxdesc.setText(f['weather'][0]['description'])
        wxdesc2.setText(f['weather'][0]['description'])

        if Config.metric:
            temper.setText('%.1d' % (f['temp']) + u'°C')  # '%.1d' Целое число
            temper2.setText('%.1d' % (f['temp']) + u'°C')
            press.setText(Config.LPressure + '%.1d' % (f['pressure']*0.750062) + ' мм.рт.ст')
            humidity.setText(Config.LHumidity + '%.0f%%' % (f['humidity']) + u', Т.росы: ' + \
                            '%.1d' % (f['dew_point']) + u'°C')  #                                   Точка Росы
# Видимость owm
            visibility = (Config.Lvisibility + '%.1d' % (f['visibility'] / 1000) + u'км, ') 

# Облачность owm
            cloudCover = (Config.LcloudCover + 
                            '%.1d' % ((f["clouds"])) + u'%, ')                           
# УФ индекс owm
            uvIndex = (Config.LuvIndex + 
                            '%.1d' % ((f["uvi"])) + u'')                            

            ccfields.setText(visibility + cloudCover + uvIndex)

            wd = bearing(f['wind_deg'])
            if Config.wind_degrees:
                wd = str(f['wind_deg']) + u'°'
            w = (Config.LWind +
                 wd + ' ' +
                 '%.1d' % (f['wind_speed']) + u'м/с,')
            if 'wind_gust' in f:
                w += (Config.Lgusting +
                      '%.1d' % (f['wind_gust']) + u'м/с')
            wind.setText(w)
            feelslike.setText(Config.LFeelslike +
                              '%.1d' % (f['feels_like']) + u'°C')
            wdate.setText("{0:%H:%M}".format(datetime.datetime.fromtimestamp(
                int(f['dt']))))
        # Config.LPrecip1hr + f['precip_1hr_metric'] + 'mm ' +
        # Config.LToday + f['precip_today_metric'] + 'mm')
        else:
            temper.setText('%.1d' % (f['temp']) + u'°F')  # '%.1d' Целое число
            temper2.setText('%.1d' % (f['temp']) + u'°F')
            press.setText(Config.LPressure + '%.1f' % f['pressure'] + 'in')
            humidity.setText(Config.LHumidity + '%.0f%%' % (f['humidity']) + u', Dew Point: ' + \
                            '%.1d' % (f['dew_point']) + u'°F')  #                                   Точка Росы

# visibility owm
            visibility = (Config.Lvisibility + '%.1d' % (f['visibility'] / 1000) + u'км, ') 

# cloudCover owm
            cloudCover = (Config.LcloudCover + 
                            '%.1d' % ((f["clouds"])) + u'%, ')                           
# UV index owm
            uvIndex = (Config.LuvIndex + 
                            '%.1d' % ((f["uvi"])) + u'')                            

            ccfields.setText(visibility + cloudCover + uvIndex)

            wd = bearing(f['wind_deg'])
            if Config.wind_degrees:
                wd = str(f['wind_deg']) + u'°'
            w = (Config.LWind +
                 wd + ' ' +
                 '%.1d' % (f['wind_speed']) + 'mph')
            if 'wind_gust' in f:
                w += (Config.Lgusting +
                      '%.1d' % (f['wind_gust']) + 'mph')
            wind.setText(w)
            feelslike.setText(Config.LFeelslike +
                              '%.1f' % (f['feels_like']) + u'°F')
            wdate.setText("{0:%H:%M}".format(datetime.datetime.fromtimestamp(
                int(f['dt']))))
    # Config.LPrecip1hr + f['precip_1hr_in'] + 'in ' +
    # Config.LToday + f['precip_today_in'] + 'in')

    for i in range(0, 3):
        f = wxdata['hourly'][i * 3 + 2]
        fl = forecast[i]

        wicon = f['weather'][0]['icon']
        wicon = owmicons[wicon]
        icon = fl.findChild(QtWidgets.QLabel, "icon")
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + wicon + ".png")
        icon.setPixmap(wxiconpixmap.scaled(
            icon.width(),
            icon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wx = fl.findChild(QtWidgets.QLabel, "wx")
        day = fl.findChild(QtWidgets.QLabel, "day")
        day.setText("{0:%A %H:%M%p}".format(datetime.datetime.fromtimestamp(  # Время 1-3 строка в столбце
            int(f['dt']))))
        s = ''
        pop = 0
        ptype = ''
        paccum = 0
        if 'pop' in f:
            pop = float(f['pop']) * 100.0
        if 'snow' in f:
            ptype = 'snow'
            paccum = float(f['snow']['1h'])
        if 'rain' in f:
            ptype = 'rain'
            paccum = float(f['rain']['1h'])

        if pop > 0.0 or ptype != '':
            s += '%.0f' % pop + '% '
        if Config.metric:
            if ptype == 'snow':
                if paccum > 0.05:
                    s += Config.LSnow + '%.0f' % paccum + 'mm '
            else:
                if paccum > 0.05:
                    s += Config.LRain + '%.0f' % paccum + 'mm '
            s += '%.0f' % f['temp'] + u'°C'
        else:
            if ptype == 'snow':
                if paccum > 0.05:
                    s += Config.LSnow + '%.0f' % paccum + 'in '
            else:
                if paccum > 0.05:
                    s += Config.LRain + '%.0f' % paccum + 'in '
            s += '%.0f' % (f['temp']) + u'°F'

        wx.setStyleSheet("#wx { font-size: " + str(int(19 * xscale * Config.fontmult)) + "px; }")
        wx.setText(f['weather'][0]['description'] + "\n" + s)

    for i in range(3, 9):
        f = wxdata['daily'][i - 3]
        wicon = f['weather'][0]['icon']
        wicon = owmicons[wicon]
        fl = forecast[i]
        icon = fl.findChild(QtWidgets.QLabel, "icon")
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + wicon + ".png")
        icon.setPixmap(wxiconpixmap.scaled(
            icon.width(),
            icon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wx = fl.findChild(QtWidgets.QLabel, "wx")
        day = fl.findChild(QtWidgets.QLabel, "day")
        day.setText("{0:%A}".format(datetime.datetime.fromtimestamp(
            int(f['dt']))))
        s = ''
        pop = 0
        ptype = ''
        paccum = 0
        if 'pop' in f:
            pop = float(f['pop']) * 100.0
        if 'rain' in f:
            ptype = 'rain'
            paccum = float(f['rain'])
        if 'snow' in f:
            ptype = 'snow'
            paccum = float(f['snow'])

        if pop > 0.05 or ptype != '':
            s += '%.0f' % pop + '% '
        if Config.metric:
            if ptype == 'snow':
                if paccum > 0.05:
                    s += Config.LSnow + '%.0f' % paccum + 'mm '
            else:
                if paccum > 0.05:
                    s += Config.LRain + '%.0f' % paccum + 'mm '
            s += '%.0f' % f['temp']['max'] + '/' + \
                 '%.0f' % f['temp']['min']
        else:
            if ptype == 'snow':
                if paccum > 0.05:
                    s += Config.LSnow + '%.1f' % paccum + 'in '
            else:
                if paccum > 0.05:
                    s += Config.LRain + '%.1f' % paccum + 'in '
            s += '%.0f' % f['temp']['max'] + '/' + \
                 '%.0f' % f['temp']['min']

        wx.setStyleSheet("#wx { font-size: " + str(int(19 * xscale * Config.fontmult)) + "px; }")
        wx.setText(f['weather'][0]['description'] + "\n" + s)

'''
def wxfinished_ds():
    global wxreply, wxdata, supress_current
    global wxicon, temper, wxdesc, press, humidity
    global wind, feelslike, wdate, bottom, forecast
    global wxicon2, temper2, wxdesc2, attribution
    global daytime

    attribution.setText("DarkSky.net")
    attribution2.setText("DarkSky.net")

    wxstr = str(wxreply.readAll(), 'utf-8')
    wxdata = json.loads(wxstr)
    f = wxdata['currently']
    if not supress_current:
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + f['icon'] + ".png")
        wxicon.setPixmap(wxiconpixmap.scaled(
            wxicon.width(), wxicon.height(), Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wxicon2.setPixmap(wxiconpixmap.scaled(
            wxicon.width(),
            wxicon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wxdesc.setText(f['summary'])
        wxdesc2.setText(f['summary'])

        if Config.metric:
            temper.setText('%.1d' % (tempm(f['temperature'])) + u'°C')  # '%.1d' Целое число
            temper2.setText('%.1d' % (tempm(f['temperature'])) + u'°C')
            press.setText(Config.LPressure + '%.1f' % f['pressure'] + 'mb')
            humidity.setText(Config.LHumidity + '%.0f%%' % (f['humidity'] * 100.0))
            wd = bearing(f['windBearing'])
            if Config.wind_degrees:
                wd = str(f['windBearing']) + u'°'
            wind.setText(Config.LWind +
                         wd + ' ' +
                         '%.1f' % (speedm(f['windSpeed'])) + u'м/с' +
                         Config.Lgusting +
                         '%.1f' % (speedm(f['windGust'])) + u'м/с')
            feelslike.setText(Config.LFeelslike +
                              '%.1f' % (tempm(f['apparentTemperature'])) + u'°C')
            wdate.setText("{0:%H:%M}".format(datetime.datetime.fromtimestamp(
                int(f['time']))))
        # Config.LPrecip1hr + f['precip_1hr_metric'] + 'mm ' +
        # Config.LToday + f['precip_today_metric'] + 'mm')
        else:
            temper.setText('%.1d' % (f['temperature']) + u'°F')  # '%.1d' Целое число
            temper2.setText('%.1d' % (f['temperature']) + u'°F')
            press.setText(Config.LPressure + '%.2f' % pressi(f['pressure']) + 'in')
            humidity.setText(Config.LHumidity + '%.0f%%' % (f['humidity'] * 100.0))
            wd = bearing(f['windBearing'])
            if Config.wind_degrees:
                wd = str(f['windBearing']) + u'°'
            wind.setText(Config.LWind +
                         wd + ' ' +
                         '%.1f' % (f['windSpeed']) + 'mph' +
                         Config.Lgusting +
                         '%.1f' % (f['windGust']) + 'mph')
            feelslike.setText(Config.LFeelslike +
                              '%.1f' % (f['apparentTemperature']) + u'°F')
            wdate.setText("{0:%H:%M}".format(datetime.datetime.fromtimestamp(
                int(f['time']))))
    # Config.LPrecip1hr + f['precip_1hr_in'] + 'in ' +
    # Config.LToday + f['precip_today_in'] + 'in')

    for i in range(0, 3):
        f = wxdata['hourly']['data'][i * 3 + 2]
        fl = forecast[i]
        icon = fl.findChild(QtWidgets.QLabel, "icon")
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + f['icon'] + ".png")
        icon.setPixmap(wxiconpixmap.scaled(
            icon.width(),
            icon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wx = fl.findChild(QtWidgets.QLabel, "wx")
        day = fl.findChild(QtWidgets.QLabel, "day")
        day.setText("{0:%A %I:%M%p}".format(datetime.datetime.fromtimestamp(
            int(f['time']))))
        s = ''
        pop = 0
        ptype = ''
        paccum = 0
        if 'precipProbability' in f:
            pop = float(f['precipProbability']) * 100.0
        if 'precipAccumulation' in f:
            paccum = float(f['precipAccumulation'])
        if 'precipType' in f:
            ptype = f['precipType']

        if pop > 0.0 or ptype != '':
            s += '%.0f' % pop + '% '
        if Config.metric:
            if ptype == 'snow':
                if paccum > 0.05:
                    s += Config.LSnow + '%.0f' % heightm(paccum) + 'mm '
            else:
                if paccum > 0.05:
                    s += Config.LRain + '%.0f' % heightm(paccum) + 'mm '
            s += '%.0f' % tempm(f['temperature']) + u'°C'
        else:
            if ptype == 'snow':
                if paccum > 0.05:
                    s += Config.LSnow + '%.0f' % paccum + 'in '
            else:
                if paccum > 0.05:
                    s += Config.LRain + '%.0f' % paccum + 'in '
            s += '%.0f' % (f['temperature']) + u'°F'

        wx.setStyleSheet("#wx { font-size: " + str(int(19 * xscale)) + "px; }")
        wx.setText(f['summary'] + "\n" + s)

    for i in range(3, 9):
        f = wxdata['daily']['data'][i - 3]
        fl = forecast[i]
        icon = fl.findChild(QtWidgets.QLabel, "icon")
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + f['icon'] + ".png")
        icon.setPixmap(wxiconpixmap.scaled(
            icon.width(),
            icon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wx = fl.findChild(QtWidgets.QLabel, "wx")
        day = fl.findChild(QtWidgets.QLabel, "day")
        day.setText("{0:%A}".format(datetime.datetime.fromtimestamp(
            int(f['time']))))
        s = ''
        pop = 0
        ptype = ''
        paccum = 0
        if 'precipProbability' in f:
            pop = float(f['precipProbability']) * 100.0
        if 'precipAccumulation' in f:
            paccum = float(f['precipAccumulation'])
        if 'precipType' in f:
            ptype = f['precipType']

        if pop > 0.05 or ptype != '':
            s += '%.0f' % pop + '% '
        if Config.metric:
            if ptype == 'snow':
                if paccum > 0.05:
                    s += Config.LSnow + '%.0f' % heightm(paccum) + 'mm '
            else:
                if paccum > 0.05:
                    s += Config.LRain + '%.0f' % heightm(paccum) + 'mm '
            s += '%.0f' % tempm(f['temperatureHigh']) + '/' + \
                 '%.0f' % tempm(f['temperatureLow'])
        else:
            if ptype == 'snow':
                if paccum > 0.05:
                    s += Config.LSnow + '%.1f' % paccum + 'in '
            else:
                if paccum > 0.05:
                    s += Config.LRain + '%.1f' % paccum + 'in '
            s += '%.0f' % f['temperatureHigh'] + '/' + \
                 '%.0f' % f['temperatureLow']

        wx.setStyleSheet("#wx { font-size: " + str(int(19 * xscale)) + "px; }")
        wx.setText(f['summary'] + "\n" + s)
'''
cc_code_map = {
    0: "Unknown",
    1000: "Clear, Sunny",
    1100: "Mostly Clear",
    1101: "Partly Cloudy",
    1102: "Mostly Cloudy",
    1001: "Cloudy",
    2000: "Fog",
    2100: "Light Fog",
    4000: "Drizzle",
    4001: "Rain",
    4200: "Light Rain",
    4201: "Heavy Rain",
    5000: "Snow",
    5001: "Flurries",
    5100: "Light Snow",
    5101: "Heavy Snow",
    6000: "Freezing Drizzle",
    6001: "Freezing Rain",
    6200: "Light Freezing Rain",
    6201: "Heavy Freezing Rain",
    7000: "Ice Pellets",
    7101: "Heavy Ice Pellets",
    7102: "Light Ice Pellets",
    8000: "Thunderstorm"
}


cc_code_icons = {
    0: "Unknown",
    1000: "clear-day",
    1100: "partly-cloudy-day",
    1101: "partly-cloudy-day",
    1102: "partly-cloudy-day",
    1001: "cloudy",
    2000: "fog",
    2100: "fog",
    4000: "sleet",
    4001: "rain",
    4200: "rain",
    4201: "rain",
    5000: "snow",
    5001: "snow",
    5100: "snow",
    5101: "snow",
    6000: "sleet",   
    6001: "sleet",
    6200: "sleet",
    6201: "sleet",
    7000: "sleet",
    7101: "sleet",
    7102: "sleet",
    8000: "thunderstorm"
}



def wxfinished_cc():
    global wxreply, wxdata, supress_current
    global wxicon, temper, wxdesc, press, humidity, ccfields
    global wind, feelslike, wdate, bottom, forecast
    global wxicon2, temper2, wxdesc2, attribution
    global daytime
    attribution.setText("tomorrow.io")
    attribution2.setText("tomorrow.io")

    wxstr = str(wxreply.readAll(), 'utf-8')
    wxdata = json.loads(wxstr)
    f = wxdata
    dt = dateutil.parser.parse(f["data"]["timelines"][0]["startTime"]) \
        .astimezone(tzlocal.get_localzone())  
    icon=f["data"]["timelines"][0]["intervals"][0]["values"]["weatherCode"]
    icon = cc_code_icons[icon]
    if not daytime:
        icon = icon.replace('-day', '-night')
    if not supress_current:
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + icon + ".png")
        wxicon.setPixmap(wxiconpixmap.scaled(
            wxicon.width(), wxicon.height(), Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wxicon2.setPixmap(wxiconpixmap.scaled(
            wxicon.width(),
            wxicon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))

        wxdesc.setText(cc_code_map[f["data"]["timelines"][0]["intervals"][0]["values"]["weatherCode"]])
        wxdesc2.setText(cc_code_map[f["data"]["timelines"][0]["intervals"][0]["values"]["weatherCode"]])

        if Config.metric:
            temper.setText('%.1d' % (f["data"]["timelines"][0]["intervals"][0]["values"]["temperature"]) + u'°C')  # '%.1d' Целое число # Температура Внутри
            temper2.setText('%.1d' % (f["data"]["timelines"][0]["intervals"][0]["values"]["temperature"]) + u'°C')  # '%.1d' Целое число
            press.setText(Config.LPressure + 
                            '%.1d' % ((f["data"]["timelines"][0]["intervals"][0]["values"]["pressureSurfaceLevel"])*0.750062) + u' мм.рт.ст')  # Давление
            humidity.setText(Config.LHumidity + '%.0f%%' % (f["data"]["timelines"][0]["intervals"][0]["values"]["humidity"]) + u', Т.росы: ' + \
                            '%.1d' % (f["data"]["timelines"][0]["intervals"][0]["values"]["dewPoint"]) + u'°C')
# Видимость
            visibility = (Config.Lvisibility + 
                            '%.1d' % ((f["data"]["timelines"][0]["intervals"][0]["values"]["visibility"])) + u'км, ')
# Облачность
            cloudCover = (Config.LcloudCover + 
                            '%.1d' % ((f["data"]["timelines"][0]["intervals"][0]["values"]["cloudCover"])) + u'%, ')                           
# УФ индекс
            uvIndex = (Config.LuvIndex + 
                            '%.1d' % ((f["data"]["timelines"][0]["intervals"][0]["values"]["uvIndex"])) + u'')                            
                            
            ccfields.setText(visibility + cloudCover + uvIndex)
            
            wd = bearing(f["data"]["timelines"][0]["intervals"][0]["values"]["windDirection"])
            if Config.wind_degrees:
                wd = str(f["data"]["timelines"][0]["intervals"][0]["values"]["windDirection"]) + u'°'
            wind.setText(Config.LWind +
                         wd + ' ' +
                         '%.1f' % (f["data"]["timelines"][0]["intervals"][0]["values"]["windSpeed"]) + u'м/с,' +
                         Config.Lgusting +
                         '%.1f' % (f["data"]["timelines"][0]["intervals"][0]["values"]["windGust"]) + u'м/с')
            feelslike.setText(Config.LFeelslike +
                              '%.1f' % ((f["data"]["timelines"][0]["intervals"][0]["values"]["temperatureApparent"])) + u'°C')
            wdate.setText(u'Данные на:  ' + "{0:%H:%M}".format(dt))  #                                                      Данные на
        # Config.LPrecip1hr + f['precip_1hr_metric'] + 'mm ' +
        # Config.LToday + f['precip_today_metric'] + 'mm')
        else:
            temper.setText('%.1d' % (f["data"]["timelines"][0]["intervals"][0]["values"]["temperature"]) + u'°F')  # '%.1d' Целое число
            temper2.setText('%.1d' % (f["data"]["timelines"][0]["intervals"][0]["values"]["temperature"]) + u'°F')
            press.setText(Config.LPressure +
                          '%.2f' % (f["data"]["timelines"][0]["intervals"][0]["values"]["pressureSurfaceLevel"]) + 'in')
            humidity.setText(Config.LHumidity + '%.0f%%' % (f["data"]["timelines"][0]["intervals"][0]["values"]["humidity"]) + u', Dew Point: ' + \
                            '%.1d' % (f["data"]["timelines"][0]["intervals"][0]["values"]["dewPoint"]) + u'°F')

# Видимость
            visibility = (Config.Lvisibility + 
                            '%.1d' % ((f["data"]["timelines"][0]["intervals"][0]["values"]["visibility"])) + u'км, ')
# Облачность
            cloudCover = (Config.LcloudCover + 
                            '%.1d' % ((f["data"]["timelines"][0]["intervals"][0]["values"]["cloudCover"])) + u'%, ')                           
# УФ индекс
            uvIndex = (Config.LuvIndex + 
                            '%.1d' % ((f["data"]["timelines"][0]["intervals"][0]["values"]["uvIndex"])) + u'')                            
                            
            ccfields.setText(visibility + cloudCover + uvIndex)

            wd = bearing(f["data"]["timelines"][0]["intervals"][0]["values"]["windDirection"])
            if Config.wind_degrees:
                wd = str(f["data"]["timelines"][0]["intervals"][0]["values"]["windDirection"]) + u'°'
            wind.setText(Config.LWind +
                         wd + ' ' +
                         '%.1f' % (f["data"]["timelines"][0]["intervals"][0]["values"]["windSpeed"]) + 'mph' +
                         Config.Lgusting +
                         '%.1f' % (f["data"]["timelines"][0]["intervals"][0]["values"]["windGust"]) + 'mph')
            feelslike.setText(Config.LFeelslike +
                              '%.1f' % (f["data"]["timelines"][0]["intervals"][0]["values"]["temperatureApparent"]) + u'°F')
            wdate.setText(u'Data on:  ' + "{0:%H:%M}".format(dt))
    # Config.LPrecip1hr + f['precip_1hr_in'] + 'in ' +
    # Config.LToday + f['precip_today_in'] + 'in')


def wxfinished_cc2():
    global wxreply2, forecast
    global daytime
    wxstr2 = str(wxreply2.readAll(), 'utf-8')
    wxdata2 = json.loads(wxstr2)
#    print(wxdata2)

    for i in range(0, 3):
        f = wxdata2["data"]["timelines"][0]["intervals"][i * 3 + 2] # 3 Часовой прогноз
        fl = forecast[i]
        wicon = f["values"]["weatherCode"]
        
        wicon = cc_code_icons[wicon] 
        dt = dateutil.parser.parse(f["startTime"]) \
            .astimezone(tzlocal.get_localzone())

        fdaytime = False
        if dt.day == datetime.datetime.now().day:
            fdaytime = daytime
        else:
            fsunrise = sun.sunrise(dt)
            fsunset = sun.sunset(dt)
#            print('calc daytime', fdaytime, dt, fsunrise, fsunset)
            if fsunrise <= dt.time() <= fsunset:
                fdaytime = True
            else:
                fdaytime = False

        if not fdaytime:
            wicon = wicon.replace('-day', '-night')
        icon = fl.findChild(QtWidgets.QLabel, "icon")
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + wicon + ".png")
        icon.setPixmap(wxiconpixmap.scaled(
            icon.width(),
            icon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wx = fl.findChild(QtWidgets.QLabel, "wx")
        day = fl.findChild(QtWidgets.QLabel, "day")
        day.setText("{0:%A %H:%M}".format(  #                            день недели и время 1-3 строка в столбце
            dateutil.parser.parse(f["startTime"]).astimezone(tzlocal.get_localzone())))  # Справа 3 часовой прогноз
        s = ''
        pop = float(f["values"]["precipitationProbability"])
        ptype = f["values"]["precipitationType"]
        if ptype == 0:
            ptype = ''
        paccum = f["values"]["precipitationIntensity"]        
        if pop > 0.0 or ptype != '':
            s += u"" '%.0f' % pop + '% '
        if Config.metric:
            if ptype == 2 :  
                if paccum > 0.01:
                    s += Config.LSnow + '%.0f' % (paccum) + u'мм/ч '
            else:
                if paccum > 0.01:
                    s += Config.LRain + '%.0f' % (paccum) + u'мм/ч '
            s += '%.0f' % (f["values"]["temperature"]) + u'°C'
        else:
            if ptype == 2 :
                if paccum > 0.01:
                    s += Config.LSnow + '%.0f' % paccum + 'in '
            else:
                if paccum > 0.01:
                    s += Config.LRain + '%.0f' % paccum + 'in '
            s += '%.0f' % (f["values"]["temperature"]) + u'°F'

        wx.setStyleSheet("#wx { font-size: " + str(int(19 * xscale * Config.fontmult)) + "px; }")
        wx.setText(cc_code_map[f["values"]["weatherCode"]] + "\n" + s)
        wx.setAlignment(Qt.AlignHCenter | Qt.AlignTop)  #             Выравнивание столбец 1-3 строка

def wxfinished_cc3():
    global wxreply3, forecast
    global daytime
    wxstr3 = str(wxreply3.readAll(), 'utf-8')
    wxdata3 = json.loads(wxstr3)
    ioff = 0

    dt = dateutil.parser.parse(
        wxdata3["data"]["timelines"][0]["startTime"] + "T00:00:00")
    if datetime.datetime.now().day != dt.day:
        ioff += 1
    for i in range(3, 9):
        f = wxdata3["data"]["timelines"][0]["intervals"][i - 3 + ioff]
        wicon = f["values"]["weatherCode"]
        wicon = cc_code_icons[wicon]
        fl = forecast[i]
        icon = fl.findChild(QtWidgets.QLabel, "icon")
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + wicon + ".png")
        icon.setPixmap(wxiconpixmap.scaled(
            icon.width(),
            icon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wx = fl.findChild(QtWidgets.QLabel, "wx")
        day = fl.findChild(QtWidgets.QLabel, "day")
        day.setText("{0:%A}".format(  #                 Дата справа столбец 4-9 строка
            dateutil.parser.parse(
                f["startTime"] + "T00:00:00"
            )
        ))
        s = ''
        pop = float(f["values"]["precipitationProbability"])
        ptype = ''
        paccum = float(f["values"]["precipitationIntensity"])
        wc = f["values"]["weatherCode"]
        wc = cc_code_icons[wc]

        if '4000' in wc:
            ptype = 'rain'
        if '4001' in wc:
            ptype = 'rain'
        if '4200' in wc:
            ptype = 'rain'
        if '4201' in wc:
            ptype = 'rain'
        if '5000' in wc:
            ptype = 'snow'
        if '5001' in wc:
            ptype = 'snow'
        if '5100' in wc:
            ptype = 'snow'
        if '5101' in wc:
            ptype = 'snow'
        if '6000' in wc:
            ptype = 'rain'
        if '6001' in wc:
            ptype = 'rain'
        if '6200' in wc:
            ptype = 'rain'
        if '6201' in wc:
            ptype = 'rain'
        if '7000' in wc:
            ptype = 'snow'
        if '7101' in wc:
            ptype = 'snow'
        if '7102' in wc:
            ptype = 'snow'
        if '8000' in wc:
            ptype = 'rain'    



        # if (pop > 0.05 and ptype == ''):
        #     if f['temp'][1]['max']['value'] > 28:
        #         ptype = 'rain'
        #     else:
        #         ptype = 'snow'
        if pop > 0.05 or ptype != '':
            s += u"" + '%.0f' % pop + '% '
        if Config.metric:            
            if ptype == 'snow':
                if paccum > 0.01:
                    s += Config.LSnow + '%.2f' % (paccum) + u'мм/ч '
            else:
                if paccum > 0.01:
                    s += Config.LRain + '%.2f' % (paccum) + u'мм/ч '
            s += '%.0f' % (f["values"]["temperatureMin"]) + '/' + \
                    '%.0f' % (f["values"]["temperatureMax"]) + '°C'
        else:
            if ptype == 'snow':
                if paccum > 0.01:
                    s += Config.LSnow + '%.1f' % (paccum) + 'in/hr '
            else:
                if paccum > 0.01:
                    s += Config.LRain + '%.1f' % paccum + 'in/hr '
            s += '%.0f' % f["values"]["temperatureMin"] + '/' + \
                    '%.0f' % f["values"]["temperatureMax"]
        wx.setStyleSheet("#wx { font-size: " + str(int(19 * xscale * Config.fontmult)) + "px; }")
        wx.setText(cc_code_map[f["values"]["weatherCode"]] + "\n" + s)
        wx.setAlignment(Qt.AlignHCenter | Qt.AlignTop)  #                 Выравнивание столбец 4-9 строка


'''
metar_cond = [
    ('CLR', '', '', 'Clear', 'clear-day', 0),
    ('NSC', '', '', 'Clear', 'clear-day', 0),
    ('SKC', '', '', 'Clear', 'clear-day', 0),
    ('FEW', '', '', 'Few Clouds', 'partly-cloudy-day', 1),
    ('NCD', '', '', 'Clear', 'clear-day', 0),
    ('SCT', '', '', 'Scattered Clouds', 'partly-cloudy-day', 2),
    ('BKN', '', '', 'Mostly Cloudy', 'partly-cloudy-day', 3),
    ('OVC', '', '', 'Cloudy', 'cloudy', 4),

    ('///', '', '', '', 'cloudy', 0),
    ('UP', '', '', '', 'cloudy', 0),
    ('VV', '', '', '', 'cloudy', 0),
    ('//', '', '', '', 'cloudy', 0),

    ('DZ', '', '', 'Drizzle', 'rain', 10),

    ('RA', 'FZ', '+', 'Heavy Freezing Rain', 'sleet', 11),
    ('RA', 'FZ', '-', 'Light Freezing Rain', 'sleet', 11),
    ('RA', 'SH', '+', 'Heavy Rain Showers', 'sleet', 11),
    ('RA', 'SH', '-', 'Light Rain Showers', 'rain', 11),
    ('RA', 'BL', '+', 'Heavy Blowing Rain', 'rain', 11),
    ('RA', 'BL', '-', 'Light Blowing Rain', 'rain', 11),
    ('RA', 'FZ', '', 'Freezing Rain', 'sleet', 11),
    ('RA', 'SH', '', 'Rain Showers', 'rain', 11),
    ('RA', 'BL', '', 'Blowing Rain', 'rain', 11),
    ('RA', '', '+', 'Heavy Rain', 'rain', 11),
    ('RA', '', '-', 'Light Rain', 'rain', 11),
    ('RA', '', '', 'Rain', 'rain', 11),

    ('SN', 'FZ', '+', 'Heavy Freezing Snow', 'snow', 12),
    ('SN', 'FZ', '-', 'Light Freezing Snow', 'snow', 12),
    ('SN', 'SH', '+', 'Heavy Snow Showers', 'snow', 12),
    ('SN', 'SH', '-', 'Light Snow Showers', 'snow', 12),
    ('SN', 'BL', '+', 'Heavy Blowing Snow', 'snow', 12),
    ('SN', 'BL', '-', 'Light Blowing Snow', 'snow', 12),
    ('SN', 'FZ', '', 'Freezing Snow', 'snow', 12),
    ('SN', 'SH', '', 'Snow Showers', 'snow', 12),
    ('SN', 'BL', '', 'Blowing Snow', 'snow', 12),
    ('SN', '', '+', 'Heavy Snow', 'snow', 12),
    ('SN', '', '-', 'Light Snow', 'snow', 12),
    ('SN', '', '', 'Rain', 'snow', 12),

    ('SG', 'BL', '', 'Blowing Snow', 'snow', 12),
    ('SG', '', '', 'Snow', 'snow', 12),
    ('GS', 'BL', '', 'Blowing Snow Pellets', 'snow', 12),
    ('GS', '', '', 'Snow Pellets', 'snow', 12),

    ('IC', '', '', 'Ice Crystals', 'snow', 13),
    ('PL', '', '', 'Ice Pellets', 'snow', 13),

    ('GR', '', '+', 'Heavy Hail', 'thuderstorm', 14),
    ('GR', '', '', 'Hail', 'thuderstorm', 14),
]
'''

'''
def temperatureApparent(f):
    t = f.temp.value('C')
    d = f.dewpt.value('C')
    h = (math.exp((17.625 * d) / (243.04 + d)) /
         math.exp((17.625 * t) / (243.04 + t)))
    t = f.temp.value('F')
    w = f.wind('MPH')
    if t > 80 and h >= 0.40:
        hi = (-42.379 + 2.04901523 * t + 10.14333127 * h - .22475541 * t * h -
              .00683783 * t * t - .05481717 * h * h + .00122874 * t * t * h +
              .00085282 * t * h * h - .00000199 * t * t * h * h)
        if h < 0.13:
            if 80.0 <= t <= 112.0:
                hi -= ((13 - h) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
        if h > 0.85:
            if 80.0 <= t <= 112.0:
                hi += ((h - 85) / 10) * ((87 - t) / 5)
        return hi
#    if t < 50 and w >= 3:
        wc = 35.74 + 0.6215 * t - 35.75 * \
             (w ** 0.16) + 0.4275 * t * (w ** 0.16)
        return wc
    return t


def wxfinished_metar():
    global metarreply
    global wxicon, temper, wxdesc, press, humidity
    global wind, feelslike, wdate, bottom
    global wxicon2, temper2, wxdesc2
    global daytime

    wxstr = str(metarreply.readAll(), 'utf-8')
    for wxline in wxstr.splitlines():
        if wxline.startswith(Config.METAR):
            wxstr = wxline
    print('wxmetar: ' + wxstr)
    f = Metar.Metar(wxstr)
    print(f)

    dt = f.time.replace(tzinfo=TimeZoneUTC()).astimezone(tzlocal.get_localzone())

    pri = -1
    weather = ''
    icon = ''
    for s in f.sky:
        for c in metar_cond:
            if s[0] == c[0]:
                if c[5] > pri:
                    pri = c[5]
                    weather = c[3]
                    icon = c[4]
    for w in f.weather:
        for c in metar_cond:
            if w[2] == c[0]:
                if c[1] > '':
                    if w[1] == c[1]:
                        if c[2] > '':
                            if w[0][0:1] == c[2]:
                                if c[5] > pri:
                                    pri = c[5]
                                    weather = c[3]
                                    icon = c[4]
                else:
                    if c[2] > '':
                        if w[0][0:1] == c[2]:
                            if c[5] > pri:
                                pri = c[5]
                                weather = c[3]
                                icon = c[4]
                    else:
                        if c[5] > pri:
                            pri = c[5]
                            weather = c[3]
                            icon = c[4]

    if not daytime:
        icon = icon.replace('-day', '-night')

    wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + icon + ".png")
    wxicon.setPixmap(wxiconpixmap.scaled(
        wxicon.width(), wxicon.height(), Qt.IgnoreAspectRatio,
        Qt.SmoothTransformation))
    wxicon2.setPixmap(wxiconpixmap.scaled(
        wxicon.width(),
        wxicon.height(),
        Qt.IgnoreAspectRatio,
        Qt.SmoothTransformation))
    wxdesc.setText(weather)
    wxdesc2.setText(weather)

    if Config.metric:
        temper.setText('%.1d' % (f.temp.value('C')) + u'°C')  #              '%.1d' Целое число
        temper2.setText('%.1d' % (f.temp.value('C')) + u'°C')
        press.setText(Config.LPressure + '%.1f' % f.press.value('MB') + 'mb')
        t = f.temp.value('C')
        d = f.dewpt.value('C')
        h = 100.0 * (math.exp((17.625 * d) / (243.04 + d)) /
                     math.exp((17.625 * t) / (243.04 + t)))
        humidity.setText(Config.LHumidity + '%.0f%%' % h)
        wd = f.wind_dir.compass()
        if Config.wind_degrees:
            wd = str(f.wind_dir.value) + u'°'
        ws = (Config.LWind +
              wd + ' ' +
              str(f.wind('KMH')) + 'km/h')
        if f.wind:
            ws += (Config.Lgusting +
                   str(f.wind('KMH')) + 'km/h')
        wind.setText(ws)
        feelslike.setText(Config.LFeelslike +
                          ('%.1f' % (tempm(temperatureApparent(f))) + u'°C'))
        wdate.setText("{0:%H:%M}".format(dt))
    # Config.LPrecip1hr + f['precip_1hr_metric'] + 'mm ' +
    # Config.LToday + f['precip_today_metric'] + 'mm')
    else:
        temper.setText('%.1d' % (f.temp.value('F')) + u'°F')  #             '%.1d' Целое число
        temper2.setText('%.1d' % (f.temp.value('F')) + u'°F')
        press.setText(Config.LPressure + '%.2f' % f.press.value('IN') + 'in')
        t = f.temp.value('C')
        d = f.dewpt.value('C')
        h = 100.0 * (math.exp((17.625 * d) / (243.04 + d)) /
                     math.exp((17.625 * t) / (243.04 + t)))
        humidity.setText(Config.LHumidity + '%.0f%%' % h)
        wd = f.wind_dir.compass()
        if Config.wind_degrees:
            wd = str(f.wind_dir.value) + u'°'
        ws = (Config.LWind +
              wd + ' ' +
              str(f.wind('MPH')) + 'mph')
        print('-ws===', ws)    

        if f.wind:
            ws += (Config.Lgusting +
                   str(f.wind('MPH')) + 'mph')
        wind.setText(ws)
        feelslike.setText(Config.LFeelslike +
                          '%.1f' % (temperatureApparent(f)) + u'°F')
        wdate.setText("{0:%H:%M} {1}".format(dt, Config.METAR))


# Config.LPrecip1hr + f['precip_1hr_in'] + 'in ' +
# Config.LToday + f['precip_today_in'] + 'in')
'''

def getwx():
    global supress_current
    supress_current = False
#    try:
#        if Config.METAR != '':
#            supress_current = True
#            getwx_metar()
#    except AttributeError:
#        pass
#
#    try:
#        ApiKeys.dsapi
#        getwx_ds()
#        return
#    except AttributeError:
#        pass

    try:
        ApiKeys.ccapi
        global cc_code_map
        try:
            cc_code_map = Config.Lcc_code_map
        except AttributeError:
            pass
        getwx_cc()
        return
    except AttributeError:
        pass

    try:
        ApiKeys.owmapi
        getwx_owm()
        return
    except AttributeError:
        pass

'''
def getwx_ds():
    global wxurl
    global wxreply
    print("getting current and forecast: " + time.ctime())
    wxurl = 'https://api.darksky.net/forecast/' + ApiKeys.dsapi + '/'
    wxurl += str(Config.location.lat) + ',' + str(Config.location.lng)
    wxurl += '?units=us&lang=' + Config.Language.lower()
    wxurl += '&r=' + str(random.random())
    print(wxurl)
    r = QUrl(wxurl)
    r = QNetworkRequest(r)
    wxreply = manager.get(r)
    wxreply.finished.connect(wxfinished_ds)
'''

def getwx_owm():
    global wxurl
    global wxreply
#    print("getting current and forecast: " + time.ctime())
    wxurl = 'https://api.openweathermap.org/data/2.5/onecall?appid=' + ApiKeys.owmapi
    wxurl += "&lat=" + str(Config.location.lat) + '&lon=' + str(Config.location.lng)

    if Config.metric:
        
        wxurl += '&units=metric'
    else:
        wxurl += '&units=imperial'

    wxurl += '&lang='+ Config.Language.lower()
    wxurl += '&r=' + str(random.random())
#    print(wxurl)
    r = QUrl(wxurl)
    r = QNetworkRequest(r)
    wxreply = manager.get(r)
    wxreply.finished.connect(wxfinished_owm)


def getwx_cc():
    global wxurl
    global wxurl2
    global wxurl3
    global wxreply
    global wxreply2
    global wxreply3
#    print("getting current: " + time.ctime())
    wxurl = 'https://api.tomorrow.io/v4/timelines?timesteps=current&apikey=' + ApiKeys.ccapi
    wxurl += "&location=" + str(Config.location.lat) + ',' + str(Config.location.lng)

    if Config.metric:
        
        wxurl += '&units=metric'  #                                          Единицы измерения
    else:
        wxurl += '&units=imperial'

    wxurl += '&fields=temperature,weatherCode,temperatureApparent,humidity,'
    wxurl += 'windSpeed,windDirection,windGust,pressureSurfaceLevel,precipitationType,'
    wxurl += 'dewPoint,visibility,cloudCover,uvIndex'
#    print(wxurl)
    r = QUrl(wxurl)
    r = QNetworkRequest(r)
    wxreply = manager.get(r)
    wxreply.finished.connect(wxfinished_cc)
#    print("getting hourly: " + time.ctime())
    wxurl2 = 'https://api.tomorrow.io/v4/timelines?timesteps=1h&apikey=' + ApiKeys.ccapi
    wxurl2 += "&location=" + str(Config.location.lat) + ',' + str(Config.location.lng)

    if Config.metric:
        
        wxurl2 += '&units=metric'  #                                          Единицы измерения
    else:
        wxurl2 += '&units=imperial'

    wxurl2 += '&fields=temperature,precipitationIntensity,precipitationType,'
    wxurl2 += 'precipitationProbability,weatherCode'
#    print(wxurl2)
    r2 = QUrl(wxurl2)
    r2 = QNetworkRequest(r2)
    wxreply2 = manager.get(r2)
    wxreply2.finished.connect(wxfinished_cc2)
#    print("getting daily: " + time.ctime())
    wxurl3 = 'https://api.tomorrow.io/v4/timelines?timesteps=1d&apikey=' + ApiKeys.ccapi 
    wxurl3 += "&location=" + str(Config.location.lat) + ',' + str(Config.location.lng)


    if Config.metric:
        
        wxurl3 += '&units=metric'  #                                          Единицы измерения
    else:
        wxurl3 += '&units=imperial'

    wxurl3 += '&fields=temperature,precipitationIntensity,precipitationType,'
    wxurl3 += 'precipitationProbability,weatherCode,temperatureMax,temperatureMin'
#    print(wxurl3)
    r3 = QUrl(wxurl3)
    r3 = QNetworkRequest(r3)
    wxreply3 = manager.get(r3)
    wxreply3.finished.connect(wxfinished_cc3)

'''
def getwx_metar():
    global metarurl
    global metarreply
    metarurl = "https://tgftp.nws.noaa.gov/data/observations/metar/stations/" + Config.METAR + ".TXT"
    print('metar url: ' + metarurl)
    r = QUrl(metarurl)
    r = QNetworkRequest(r)
    metarreply = manager.get(r)
    metarreply.finished.connect(wxfinished_metar)
'''

def getallwx():
    getwx()


def qtstart():
    global ctimer, wxtimer, temptimer
    global manager
    global objradar1
    global objradar2
    global objradar3
    global objradar4
    global sun, daytime, sunrise, sunset

    dt = datetime.datetime.now(tz=tzlocal.get_localzone())
    sun = SunTimes(Config.location.lat, Config.location.lng)
    sunrise = sun.sunrise(dt)
    sunset = sun.sunset(dt)
    if sunrise <= dt.time() <= sunset:
        daytime = True
    else:
        daytime = False

    getallwx()

    gettemp()

    objradar1.start(Config.radar_refresh * 60)
    objradar1.wxstart()
    objradar2.start(Config.radar_refresh * 60)
    objradar2.wxstart()
    objradar3.start(Config.radar_refresh * 60)
    objradar4.start(Config.radar_refresh * 60)

    ctimer = QtCore.QTimer()
    ctimer.timeout.connect(tick)
    ctimer.start(1000)

    wxtimer = QtCore.QTimer()
    wxtimer.timeout.connect(getallwx)
    wxtimer.start(int(1000 * Config.weather_refresh * 60 + random.uniform(1000, 10000)))

    temptimer = QtCore.QTimer()
    temptimer.timeout.connect(gettemp)
    temptimer.start(int(1000 * 10 * 60 + random.uniform(1000, 10000)))

    if Config.useslideshow:
        objimage1.start(Config.slide_time)


class SlideShow(QtWidgets.QLabel):
    def __init__(self, parent, rect, myname):
        self.myname = myname
        self.rect = rect
        QtWidgets.QLabel.__init__(self, parent)

        self.pause = False
        self.count = 0
        self.img_list = []
        self.img_inc = 1

        self.get_images()

        self.setObjectName("slideShow")
        self.setGeometry(rect)
        self.setStyleSheet("#slideShow { background-color: " +
                           Config.slide_bg_color + "; }")
        self.setAlignment(Qt.AlignHCenter | Qt.AlignCenter)

        self.timer = None

    def start(self, interval):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.run_ss)
        self.timer.start(1000 * interval + random.uniform(1, 10))
        self.run_ss()

    def stop(self):
        try:
            self.timer.stop()
            self.timer = None
        except AttributeError:
            pass

    def run_ss(self):
        self.get_images()
        self.switch_image()

    def switch_image(self):
        if self.img_list:
            if not self.pause:
                self.count += self.img_inc
                if self.count >= len(self.img_list):
                    self.count = 0
                self.show_image(self.img_list[self.count])
                self.img_inc = 1

    def show_image(self, image):
        image = QtGui.QImage(image)

        bg = QtGui.QPixmap.fromImage(image)
        self.setPixmap(bg.scaled(
            self.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation))

    def get_images(self):
        self.get_local(Config.slides)

    def play_pause(self):
        if not self.pause:
            self.pause = True
        else:
            self.pause = False

    def prev_next(self, direction):
        self.img_inc = direction
        self.timer.stop()
        self.switch_image()
        self.timer.start()

    def get_local(self, path):
        try:
            dir_content = os.listdir(path)
            for each in dir_content:
                full_file = os.path.join(path, each)
                if os.path.isfile(full_file) and (full_file.lower().endswith('png')
                                                  or full_file.lower().endswith('jpg')):
                    self.img_list.append(full_file)
        except OSError:
            print("path '%s' doesn't exists." % path)


class Radar(QtWidgets.QLabel):

    def __init__(self, parent, radar, rect, myname):
        global xscale, yscale
        self.myname = myname
        self.rect = rect
        self.anim = 5
        self.zoom = radar["zoom"]
        self.point = radar["center"]
        self.radar = radar
        self.baseurl = self.mapurl(radar, rect, False)
#        print("map base url for " + self.myname + ": " + self.baseurl)

        mb = 0
        try:
            mb = Config.usemapbox
        except AttributeError:
            pass
        if mb:
            if 'overlay' in radar:
                if radar['overlay'] != '':
                    self.overlayurl = self.mapurl(radar, rect, True)
#                    print("map overlay url for " + self.myname + ": " + self.overlayurl)

        QtWidgets.QLabel.__init__(self, parent)
        self.interval = Config.radar_refresh * 60
        self.lastwx = 0
        self.retries = 0
        self.corners = get_corners(self.point, self.zoom,
                                   rect.width(), rect.height())
        self.baseTime = 0
        self.cornerTiles = {
            "NW": get_tile_xy(LatLng(self.corners["N"],
                                     self.corners["W"]), self.zoom),
            "NE": get_tile_xy(LatLng(self.corners["N"],
                                     self.corners["E"]), self.zoom),
            "SE": get_tile_xy(LatLng(self.corners["S"],
                                     self.corners["E"]), self.zoom),
            "SW": get_tile_xy(LatLng(self.corners["S"],
                                     self.corners["W"]), self.zoom)
        }
        self.tiles = []
        self.tiletails = []
        self.totalWidth = 0
        self.totalHeight = 0
        self.tilesWidth = 0
        self.tilesHeight = 0

        self.setObjectName("radar")
        self.setGeometry(rect)
        self.setStyleSheet("#radar { background-color: grey; }")
        self.setAlignment(Qt.AlignCenter)

        self.wwx = QtWidgets.QLabel(self)
        self.wwx.setObjectName("wx")
        self.wwx.setStyleSheet("#wx { background-color: transparent; }")
        self.wwx.setGeometry(0, 0, rect.width(), rect.height())

        self.overlay = QtWidgets.QLabel(self)
        self.overlay.setObjectName("overlay")
        self.overlay.setStyleSheet(
            "#overlay { background-color: transparent; }")
        self.overlay.setGeometry(0, 0, rect.width(), rect.height())

        self.wmk = QtWidgets.QLabel(self)
        self.wmk.setObjectName("mk")
        self.wmk.setStyleSheet("#mk { background-color: transparent; }")
        self.wmk.setGeometry(0, 0, rect.width(), rect.height())

        for y in range(int(self.cornerTiles["NW"]["Y"]),
                       int(self.cornerTiles["SW"]["Y"]) + 1):
            self.totalHeight += 256
            self.tilesHeight += 1
            for x in range(int(self.cornerTiles["NW"]["X"]),
                           int(self.cornerTiles["NE"]["X"]) + 1):
                tile = {"X": x, "Y": y}
                self.tiles.append(tile)
                if 'color' not in radar:
                    radar['color'] = 6
                if 'smooth' not in radar:
                    radar['smooth'] = 1
                if 'snow' not in radar:
                    radar['snow'] = 1
                tail = "/256/%d/%d/%d/%d/%d_%d.png" % (self.zoom, x, y,
                                                       radar['color'],
                                                       radar['smooth'],
                                                       radar['snow'])
                if 'oldcolor' in radar:
                    tail = "/256/%d/%d/%d.png?color=%d" % (self.zoom, x, y,
                                                           radar['color'])
                self.tiletails.append(tail)
        for x in range(int(self.cornerTiles["NW"]["X"]),
                       int(self.cornerTiles["NE"]["X"]) + 1):
            self.totalWidth += 256
            self.tilesWidth += 1
        self.frameImages = []
        self.frameIndex = 0
        self.displayedFrame = 0
        self.ticker = 0
        self.lastget = 0

        self.getTime = 0
        self.getIndex = 0
        self.tileurls = []
        self.tileQimages = []
        self.tilereq = None
        self.tilereply = None
        self.basepixmap = None
        self.mkpixmap = None
        self.basereq = None
        self.basereply = None
        self.timer = None
        self.overlayreq = None
        self.overlayreply = None
        self.overlaypixmap = None

    def rtick(self):
        if time.time() > (self.lastget + self.interval):
            self.get(int(time.time()))
            self.lastget = time.time()
        if len(self.frameImages) < 1:
            return
        if self.displayedFrame == 0:
            self.ticker += 1
            if self.ticker < 5:
                return
        self.ticker = 0
        try:
            f = self.frameImages[self.displayedFrame]
            self.wwx.setPixmap(f["image"])
        except IndexError:
            pass
        self.displayedFrame += 1
        if self.displayedFrame >= len(self.frameImages):
            self.displayedFrame = 0

    def get(self, t=0):
        t = int(t / 600) * 600
        if t > 0:
            if self.baseTime == t:
                return
        if t == 0:
            t = self.baseTime
        else:
            self.baseTime = t
        newf = []
        for f in self.frameImages:
            if f["time"] >= (t - self.anim * 600):
                newf.append(f)
        self.frameImages = newf
        firstt = t - self.anim * 600
        for tt in range(firstt, t + 1, 600):
#            print("get... " + str(tt) + " " + self.myname)
            gotit = False
            for f in self.frameImages:
                if f["time"] == tt:
                    gotit = True
            if not gotit:
                self.get_tiles(tt)
                break

    def get_tiles(self, t, i=0):
        t = int(t / 600) * 600
        self.getTime = t
        self.getIndex = i
        if i == 0:
            self.tileurls = []
            self.tileQimages = []
            for tt in self.tiletails:
                tileurl = "https://tilecache.rainviewer.com/v2/radar/%d/%s" \
                          % (t, tt)
                self.tileurls.append(tileurl)
#        print(self.myname + " " + str(self.getIndex) + " " + self.tileurls[i])
        self.tilereq = QNetworkRequest(QUrl(self.tileurls[i]))
        self.tilereply = manager.get(self.tilereq)
        self.tilereply.finished.connect(self.get_tilesreply)

    def get_tilesreply(self):
#        print("get_tilesreply " + str(self.getIndex))
        if self.tilereply.error() != QNetworkReply.NoError:
            return
        self.tileQimages.append(QImage())
        self.tileQimages[self.getIndex].loadFromData(self.tilereply.readAll())
        self.getIndex = self.getIndex + 1
        if self.getIndex < len(self.tileurls):
            self.get_tiles(self.getTime, self.getIndex)
        else:
            self.combine_tiles()
            self.get()

    def combine_tiles(self):
        ii = QImage(self.tilesWidth * 256, self.tilesHeight * 256,
                    QImage.Format_ARGB32)
        painter = QPainter()
        painter.begin(ii)
        painter.setPen(QColor(255, 255, 255, 255))
        painter.setFont(QFont("Arial", 24))
        i = 0
        xo = self.cornerTiles["NW"]["X"]
        xo = int((int(xo) - xo) * 256)
        yo = self.cornerTiles["NW"]["Y"]
        yo = int((int(yo) - yo) * 256)
        for y in range(0, self.totalHeight, 256):
            for x in range(0, self.totalWidth, 256):
                if self.tileQimages[i].format() == 5:
                    painter.drawImage(x, y, self.tileQimages[i])
                i += 1
        painter.end()
        self.tileQimages = []
        ii2 = ii.copy(-xo, -yo, self.rect.width(), self.rect.height())
        painter2 = QPainter()
        painter2.begin(ii2)
        timestamp = "{0:%H:%M} rainviewer.com".format(
            datetime.datetime.fromtimestamp(self.getTime))
        painter2.setPen(QColor(63, 63, 63, 255))
        painter2.setFont(QFont("Arial", 12))  #             Шрифт rainviewer.com на карте вверху
        painter2.setRenderHint(QPainter.TextAntialiasing)
        painter2.drawText(3 - 1, 12 - 1, timestamp)
        painter2.drawText(3 + 2, 12 + 1, timestamp)
        painter2.setPen(QColor(192, 192, 192, 255))  #      Цвет rainviewer.com на карте вверху
        painter2.drawText(3, 12, timestamp)
        painter2.drawText(3 + 1, 12, timestamp)
        painter2.end()
        ii3 = QPixmap(ii2)
        self.frameImages.append({"time": self.getTime, "image": ii3})

    def mapurl(self, radar, rect, overlayonly):
        mb = 0
        try:
            mb = Config.usemapbox
        except AttributeError:
            pass
        if mb:
            if overlayonly:
                return self.mapboxoverlayurl(radar, rect)
            else:
                return self.mapboxbaseurl(radar, rect)
        else:
            return self.googlemapurl(radar, rect)

    @staticmethod
    def mapboxbaseurl(radar, rect):
        #  note we're using google maps zoom factor.
        #  Mapbox equivalent zoom is one less
        #  They seem to be using 512x512 tiles instead of 256x256
        basemap = 'mapbox/satellite-streets-v11'
        hide_attribution = ''
        if 'basemap' in radar:
            basemap = radar['basemap']
        if 'overlay' in radar:
            if radar['overlay'] != '':
                hide_attribution = '&attribution=false&logo=false'
        return 'https://api.mapbox.com/styles/v1/' + \
               basemap + \
               '/static/' + \
               str(radar['center'].lng) + ',' + \
               str(radar['center'].lat) + ',' + \
               str(radar['zoom']-1) + ',0,0/' + \
               str(rect.width()) + 'x' + str(rect.height()) + \
               '?access_token=' + ApiKeys.mbapi + \
               hide_attribution

    @staticmethod
    def mapboxoverlayurl(radar, rect):
        #  note we're using google maps zoom factor.
        #  Mapbox equivalent zoom is one less
        #  They seem to be using 512x512 tiles instead of 256x256
        overlay = ''
        if 'overlay' in radar:
            overlay = radar['overlay']
        return 'https://api.mapbox.com/styles/v1/' + \
               overlay + \
               '/static/' + \
               str(radar['center'].lng) + ',' + \
               str(radar['center'].lat) + ',' + \
               str(radar['zoom']-1) + ',0,0/' + \
               str(rect.width()) + 'x' + str(rect.height()) + \
               '?access_token=' + ApiKeys.mbapi

    @staticmethod
    def googlemapurl(radar, rect):
        urlp = []
        if len(ApiKeys.googleapi) > 0:
            urlp.append('key=' + ApiKeys.googleapi)
        urlp.append(
            'center=' + str(radar['center'].lat) +
            ',' + str(radar['center'].lng))
        zoom = radar['zoom']
        rsize = rect.size()
        if rsize.width() > 640 or rsize.height() > 640:
            rsize = QtCore.QSize(int(rsize.width() / 2), int(rsize.height() / 2))
            zoom -= 1
        urlp.append('zoom=' + str(zoom))
        urlp.append('size=' + str(rsize.width()) + 'x' + str(rsize.height()))
        urlp.append('maptype=hybrid')

        return 'http://maps.googleapis.com/maps/api/staticmap?' + \
               '&'.join(urlp)

    def basefinished(self):
        if self.basereply.error() != QNetworkReply.NoError:
            return
        self.basepixmap = QPixmap()
        self.basepixmap.loadFromData(self.basereply.readAll())
        if self.basepixmap.size() != self.rect.size():
            self.basepixmap = self.basepixmap.scaled(self.rect.size(),
                                                     Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation)
        self.setPixmap(self.basepixmap)

        # make marker pixmap
        self.mkpixmap = QPixmap(self.basepixmap.size())
        self.mkpixmap.fill(Qt.transparent)
        br = QBrush(QColor(Config.dimcolor))
        painter = QPainter()
        painter.begin(self.mkpixmap)
        painter.fillRect(0, 0, self.mkpixmap.width(),
                         self.mkpixmap.height(), br)
        for marker in self.radar['markers']:
            if 'visible' not in marker or marker['visible'] == 1:
                pt = get_point(marker["location"], self.point, self.zoom,
                               self.rect.width(), self.rect.height())
                mk2 = QImage()
                mkfile = 'teardrop'
                if 'image' in marker:
                    mkfile = marker['image']
                if os.path.dirname(mkfile) == '':
                    mkfile = os.path.join('markers', mkfile)
                if os.path.splitext(mkfile)[1] == '':
                    mkfile += '.png'
                mk2.load(mkfile)
                if mk2.format != QImage.Format_ARGB32:
                    mk2 = mk2.convertToFormat(QImage.Format_ARGB32)
                mkh = 80  # self.rect.height() / 5
                if 'size' in marker:
                    if marker['size'] == 'small':
                        mkh = 64
                    if marker['size'] == 'mid':
                        mkh = 70
                    if marker['size'] == 'tiny':
                        mkh = 40
                if 'color' in marker:
                    c = QColor(marker['color'])
                    (cr, cg, cb, ca) = c.getRgbF()
                    for x in range(0, mk2.width()):
                        for y in range(0, mk2.height()):
                            (r, g, b, a) = QColor.fromRgba(
                                           mk2.pixel(x, y)).getRgbF()
                            r = r * cr
                            g = g * cg
                            b = b * cb
                            mk2.setPixel(x, y, QColor.fromRgbF(r, g, b, a)
                                         .rgba())
                mk2 = mk2.scaledToHeight(mkh, 1)
                painter.drawImage(int(pt.x-mkh / 2), int(pt.y-mkh / 2), mk2)

        painter.end()

        self.wmk.setPixmap(self.mkpixmap)

    def overlayfinished(self):
        if self.overlayreply.error() != QNetworkReply.NoError:
            return
        self.overlaypixmap = QPixmap()
        self.overlaypixmap.loadFromData(self.overlayreply.readAll())
        if self.overlaypixmap.size() != self.rect.size():
            self.overlaypixmap = self.overlaypixmap.scaled(
                                            self.rect.size(),
                                            Qt.KeepAspectRatio,
                                            Qt.SmoothTransformation)
        self.overlay.setPixmap(self.overlaypixmap)

    def getbase(self):
        global manager
        self.basereq = QNetworkRequest(QUrl(self.baseurl))
        self.basereply = manager.get(self.basereq)
        self.basereply.finished.connect(self.basefinished)

    def getoverlay(self):
        global manager
        self.overlayreq = QNetworkRequest(QUrl(self.overlayurl))
        self.overlayreply = manager.get(self.overlayreq)
        self.overlayreply.finished.connect(self.overlayfinished)

    def start(self, interval=0):
        if interval > 0:
            self.interval = interval
        self.getbase()

        mb = 0
        try:
            mb = Config.usemapbox
        except AttributeError:
            pass
        if mb:
            if 'overlay' in self.radar:
                if self.radar['overlay'] != '':
                    self.getoverlay()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.rtick)
        self.lastget = time.time() - self.interval + random.uniform(3, 10)

    def wxstart(self):
#        print("wxstart for " + self.myname)
        self.timer.start(200)

    def wxstop(self):
#        print("wxstop for " + self.myname)
        self.timer.stop()

    def stop(self):
        try:
            self.timer.stop()
            self.timer = None
        except AttributeError:
            pass


def realquit():
    QtWidgets.QApplication.exit(0)


def myquit():
    global objradar1, objradar2, objradar3, objradar4
    global ctimer, wtimer, temptimer

    objradar1.stop()
    objradar2.stop()
    objradar3.stop()
    objradar4.stop()
    ctimer.stop()
    wxtimer.stop()
    temptimer.stop()
    if Config.useslideshow:
        objimage1.stop()

    QtCore.QTimer.singleShot(30, realquit)


def fixupframe(frame, onoff):
    for child in frame.children():
        if isinstance(child, Radar):
            if onoff:
                # print("calling wxstart on radar on ",frame.objectName())
                child.wxstart()
            else:
                # print("calling wxstop on radar on ",frame.objectName())
                child.wxstop()


def nextframe(plusminus):
    global frames, framep
    frames[framep].setVisible(False)
    fixupframe(frames[framep], False)
    framep += plusminus
    if framep >= len(frames):
        framep = 0
    if framep < 0:
        framep = len(frames) - 1
    frames[framep].setVisible(True)
    fixupframe(frames[framep], True)


class MyMain(QtWidgets.QWidget):

    def keyPressEvent(self, event):
        global weatherplayer, lastkeytime
        if isinstance(event, QtGui.QKeyEvent):
            # print(event.key(), format(event.key(), '08x'))
            if event.key() == Qt.Key_F4:
                myquit()
            if event.key() == Qt.Key_F2:
                if time.time() > lastkeytime:
                    if weatherplayer is None:
                        weatherplayer = Popen(
                            ["mpg123", "-q", Config.noaastream])
                    else:
                        weatherplayer.kill()
                        weatherplayer = None
                lastkeytime = time.time() + 2
            if event.key() == Qt.Key_Space:
                nextframe(1)
            if event.key() == Qt.Key_Left:
                nextframe(-1)
            if event.key() == Qt.Key_Right:
                nextframe(1)
            if event.key() == Qt.Key_R:  # Key '*'
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/rainbow.py")

            if event.key() == Qt.Key_P:  # Key '#'
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/all_leds_off.py")

            if event.key() == Qt.Key_Up:  # Key_UP, NEOPIXEL, GPIO 25, кнопка на корпусе
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/rainbow.py")

            if event.key() == Qt.Key_VolumeUp:  # Кнопка на пульте ВВЕРХ
                os.popen("DISPLAY=:0 /home/pi/PiClock/scripts/osd.sh 1%+")

            if event.key() == Qt.Key_VolumeDown:  # Кнопка на пульте ВНИЗ
                os.popen("DISPLAY=:0 /home/pi/PiClock/scripts/osd.sh 1%-")

            if event.key() == Qt.Key_O:  # Кнопка на пульте 'OK'
                os.popen("killall -9 -q mpg123")

            if event.key() == Qt.Key_1:  # Key 1
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/red.py")

            if event.key() == Qt.Key_2:  # Key 2
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/orange.py")

            if event.key() == Qt.Key_3:  # Key 3
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/yellow.py")

            if event.key() == Qt.Key_4:  # Key 4
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/green.py")

            if event.key() == Qt.Key_5:  # Key 5
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/skyblue.py")

            if event.key() == Qt.Key_6:  # Key 6
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/blue.py")

            if event.key() == Qt.Key_7:  # Key 7
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/purple.py")

            if event.key() == Qt.Key_8:  # Key 8
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/dim_light.py")

            if event.key() == Qt.Key_9:  # Key 9
                os.popen("sudo pkill -f 'PiClock/Leds'")
                os.popen("sudo /usr/bin/python3  /home/pi/PiClock/Leds/light.py")

            if event.key() == Qt.Key_F6:  # Previous Image
                objimage1.prev_next(-1)
            if event.key() == Qt.Key_F7:  # Next Image
                objimage1.prev_next(1)
            if event.key() == Qt.Key_F8:  # Play/Pause
                objimage1.play_pause()
            if event.key() == Qt.Key_F9:  # Foreground Toggle
                if foreGround.isVisible():
                    foreGround.hide()
                else:
                    foreGround.show()

    def mousePressEvent(self, event):
        if type(event) == QtGui.QMouseEvent:
            nextframe(1)


configname = 'Config'

if len(sys.argv) > 1:
    configname = sys.argv[1]

if not os.path.isfile(configname + ".py"):
#    print("Config file not found %s" % configname + ".py")
    exit(1)

Config = __import__(configname)

# define default values for new/optional config variables.

try:
    Config.location
except AttributeError:
    Config.location = Config.wulocation

try:
    Config.metric
except AttributeError:
    Config.metric = 0

try:
    Config.weather_refresh
except AttributeError:
    Config.weather_refresh = 30  # minutes

try:
    Config.radar_refresh
except AttributeError:
    Config.radar_refresh = 10  # minutes

try:
    Config.fontattr
except AttributeError:
    Config.fontattr = ''

try:
    Config.dimcolor
except AttributeError:
    Config.dimcolor = QColor('#000000')
    Config.dimcolor.setAlpha(0)

try:
    Config.DateLocale
except AttributeError:
    Config.DateLocale = ''

try:
    Config.wind_degrees
except AttributeError:
    Config.wind_degrees = 0

try:
    Config.digital
except AttributeError:
    Config.digital = 0

try:
    Config.Language
except AttributeError:
    try:
        Config.Language = Config.wuLanguage
    except AttributeError:
        Config.Language = "en"

try:
    Config.fontmult
except AttributeError:
    Config.fontmult = 1.0

try:
    Config.LPressure
except AttributeError:
    Config.LPressure = "Pressure "
    Config.LHumidity = "Humidity "
    Config.LWind = "Wind "
    Config.Lgusting = " gusting "
    Config.LFeelslike = "Feels like "
    Config.LPrecip1hr = " Precip 1hr:"
    Config.LToday = "Today: "
    Config.LSunRise = "Sun Rise:"
    Config.LSet = " Set: "
    Config.LMoonPhase = " Moon Phase:"
    Config.LInsideTemp = "Inside Temp "
    Config.LRain = " Rain: "
    Config.LSnow = " Snow: "

try:
    Config.Lmoon1
    Config.Lmoon2
    Config.Lmoon3
    Config.Lmoon4
    Config.Lmoon5
    Config.Lmoon6
    Config.Lmoon7
    Config.Lmoon8
except AttributeError:
    Config.Lmoon1 = 'New Moon'
    Config.Lmoon2 = 'Waxing Crescent'
    Config.Lmoon3 = 'First Quarter'
    Config.Lmoon4 = 'Waxing Gibbous'
    Config.Lmoon5 = 'Full Moon'
    Config.Lmoon6 = 'Waning Gibbous'
    Config.Lmoon7 = 'Third Quarter'
    Config.Lmoon8 = 'Waning Crescent'

try:
    Config.digitalformat2
except AttributeError:
    Config.digitalformat2 = "{0:%H:%M:%S}"

try:
    Config.useslideshow
except AttributeError:
    Config.useslideshow = 0

#
# Check if Mapbox API key is set, and use mapbox if so
try:
    if ApiKeys.mbapi[:3].lower() == "pk.":
        Config.usemapbox = 1
except AttributeError:
    Config.usemapbox = 0

try:
    if Config.METAR != '':
        from metar import Metar
except AttributeError:
    pass

lastmin = -1
lastday = -1
pdy = ""
lasttimestr = ""
weatherplayer = None
lastkeytime = 0
lastapiget = time.time()

app = QtWidgets.QApplication(sys.argv)
desktop = app.desktop()
rec = desktop.screenGeometry()
height = rec.height()
width = rec.width()

signal.signal(signal.SIGINT, myquit)

w = MyMain()
w.setWindowTitle(os.path.basename(__file__))

w.setStyleSheet("QWidget { background-color: black;}")

# fullbgpixmap = QtGui.QPixmap(Config.background)
# fullbgrect = fullbgpixmap.rect()
# xscale = float(width)/fullbgpixmap.width()
# yscale = float(height)/fullbgpixmap.height()

xscale = float(width) / 1440.0
yscale = float(height) / 900.0

frames = []
framep = 0

frame1 = QtWidgets.QFrame(w)
frame1.setObjectName("frame1")
frame1.setGeometry(0, 0, width, height)
frame1.setStyleSheet("#frame1 { background-color: black; border-image: url(" +
                     Config.background + ") 0 0 0 0 stretch stretch;}")
frames.append(frame1)

if Config.useslideshow:
    imgRect = QtCore.QRect(0, 0, width, height)
    objimage1 = SlideShow(frame1, imgRect, "image1")

frame2 = QtWidgets.QFrame(w)
frame2.setObjectName("frame2")
frame2.setGeometry(0, 0, width, height)
frame2.setStyleSheet("#frame2 { background-color: blue; border-image: url(" +
                     Config.background + ") 0 0 0 0 stretch stretch;}")
frame2.setVisible(False)
frames.append(frame2)

# frame3 = QtWidgets.QFrame(w)
# frame3.setObjectName("frame3")
# frame3.setGeometry(0,0,width,height)
# frame3.setStyleSheet("#frame3 { background-color: blue; border-image:
#       url("+Config.background+") 0 0 0 0 stretch stretch;}")
# frame3.setVisible(False)
# frames.append(frame3)

foreGround = QtWidgets.QFrame(frame1)
foreGround.setObjectName("foreGround")
foreGround.setStyleSheet("#foreGround { background-color: transparent; }")
foreGround.setGeometry(0, 0, width, height)

squares1 = QtWidgets.QFrame(foreGround)
squares1.setObjectName("squares1")
squares1.setGeometry(0, int(height - yscale * 600), int(xscale * 340), int(yscale * 600))
squares1.setStyleSheet(
    "#squares1 { background-color: transparent; border-image: url(" +
    Config.squares1 +
    ") 0 0 0 0 stretch stretch;}")

squares2 = QtWidgets.QFrame(foreGround)
squares2.setObjectName("squares2")
squares2.setGeometry(int(width - xscale * 340), 0, int(xscale * 340), int(yscale * 900))
squares2.setStyleSheet(
    "#squares2 { background-color: transparent; border-image: url(" +
    Config.squares2 +
    ") 0 0 0 0 stretch stretch;}")

if not Config.digital:
    clockface = QtWidgets.QFrame(foreGround)
    clockface.setObjectName("clockface")
    clockrect = QtCore.QRect(
        int(width / 2 - height * .4),
        int(height * .45 - height * .4),
        int(height * .8),
        int(height * .8))
    clockface.setGeometry(clockrect)
    clockface.setStyleSheet(
        "#clockface { background-color: transparent; border-image: url(" +
        Config.clockface +
        ") 0 0 0 0 stretch stretch;}")

    hourhand = QtWidgets.QLabel(foreGround)
    hourhand.setObjectName("hourhand")
    hourhand.setStyleSheet("#hourhand { background-color: transparent; }")

    minhand = QtWidgets.QLabel(foreGround)
    minhand.setObjectName("minhand")
    minhand.setStyleSheet("#minhand { background-color: transparent; }")

    sechand = QtWidgets.QLabel(foreGround)
    sechand.setObjectName("sechand")
    sechand.setStyleSheet("#sechand { background-color: transparent; }")

    hourpixmap = QtGui.QPixmap(Config.hourhand)
    hourpixmap2 = QtGui.QPixmap(Config.hourhand)
    minpixmap = QtGui.QPixmap(Config.minhand)
    minpixmap2 = QtGui.QPixmap(Config.minhand)
    secpixmap = QtGui.QPixmap(Config.sechand)
    secpixmap2 = QtGui.QPixmap(Config.sechand)
else:
    clockface = QtWidgets.QLabel(foreGround)
    clockface.setObjectName("clockface")
    clockrect = QtCore.QRect(
        width / 2 - height * .4,
        height * .45 - height * .4,
        height * .8,
        height * .8)
    clockface.setGeometry(clockrect)
    dcolor = QColor(Config.digitalcolor).darker(0).name()
    lcolor = QColor(Config.digitalcolor).lighter(120).name()
    clockface.setStyleSheet(
        "#clockface { background-color: transparent; font-family:sans-serif;" +
        " font-weight: light; color: " +
        lcolor +
        "; background-color: transparent; font-size: " +
        str(int(Config.digitalsize * xscale)) +
        "px; " +
        Config.fontattr +
        "}")
    clockface.setAlignment(Qt.AlignCenter)
    clockface.setGeometry(clockrect)
    glow = QtWidgets.QGraphicsDropShadowEffect()
    glow.setOffset(0)
    glow.setBlurRadius(50)
    glow.setColor(QColor(dcolor))
    clockface.setGraphicsEffect(glow)

radar1rect = QtCore.QRect(int(3 * xscale), int(344 * yscale), int(300 * xscale), int(275 * yscale))
objradar1 = Radar(foreGround, Config.radar1, radar1rect, "radar1")

radar2rect = QtCore.QRect(int(3 * xscale), int(622 * yscale), int(300 * xscale), int(275 * yscale))
objradar2 = Radar(foreGround, Config.radar2, radar2rect, "radar2")

radar3rect = QtCore.QRect(int(13 * xscale), \
    int(10 * yscale), int(700 * xscale), int(740 * yscale))  
objradar3 = Radar(frame2, Config.radar3, radar3rect, "radar3")  #           Левая карта на 2 стр

radar4rect = QtCore.QRect(int(726 * xscale), \
    int(10 * yscale), int(700 * xscale), int(740 * yscale))  
objradar4 = Radar(frame2, Config.radar4, radar4rect, "radar4")  #           Правая карта на 2 стр

#                     Дата Верхняя строка
datex = QtWidgets.QLabel(foreGround)
datex.setObjectName("datex")
datex.setStyleSheet("#datex { font-family:sans-serif; color: " +   
                    Config.textcolorTopLine +  #                             Цвет верхняя строка      
                    "; background-color: transparent; font-size: " +
                    str(int(50 * xscale * Config.fontmult)) +
                    "px; " +
                    Config.fontattr +  #                                     Шрифт
                    "}")
datex.setAlignment(Qt.AlignHCenter | Qt.AlignTop)  #                        Выравнивание
datex.setGeometry(-50, 0, width, int(100 * yscale))

#                     Дата на второй странице
datex2 = QtWidgets.QLabel(frame2)
datex2.setObjectName("datex2")
datex2.setStyleSheet("#datex2 { font-family:sans-serif; color: " +
                     Config.textcolorDatex2  +  #                      Цвет День недели на второй странице
                     "; background-color: transparent; font-size: " +
                     str(int(50 * xscale * Config.fontmult)) + "px; " +
                     Config.fontattr +
                     "}")
datex2.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
datex2.setGeometry(int(600 * xscale), int(760 * yscale), int(960 * xscale), 100)  # Дата на второй странице
datey2 = QtWidgets.QLabel(frame2)
datey2.setObjectName("datey2")
datey2.setStyleSheet("#datey2 { font-family:sans-serif; color: " +
                     Config.textcolorDatey2 +  #                       Цвет Время на 2 стр 
                     "; background-color: transparent; font-size: " +
                     str(int(50 * xscale * Config.fontmult)) +
                     "px; " +
                     Config.fontattr +  
                     "}")
datey2.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
datey2.setGeometry(int(980 * xscale), int(840 * yscale), int(640 * xscale), 100)  # Время на 2 стр

#                     Имя сайта погоды вверху слева
attribution = QtWidgets.QLabel(foreGround)
attribution.setObjectName("attribution")
attribution.setStyleSheet("#attribution { " +
                          " background-color: transparent; color: " +
                          Config.textcolor + 
                          "; font-size: " +
                          str(int(12 * xscale)) +
                          "px; " +
                          Config.fontattr +
                          "}")
attribution.setAlignment(Qt.AlignTop)
attribution.setGeometry(int(6 * xscale), \
    int(3 * yscale), int(150 * xscale), 100) 

#                       Иконка вверху слева
ypos = -25
wxicon = QtWidgets.QLabel(foreGround)
wxicon.setObjectName("wxicon")
wxicon.setStyleSheet("#wxicon { background-color: transparent; }")
wxicon.setGeometry(int(75 * xscale), \
    int(0 * yscale), int(130 * xscale), int(130 * yscale))  

#                       Имя сайта погоды на 2 стр внизу слева
attribution2 = QtWidgets.QLabel(frame2)
attribution2.setObjectName("attribution2")
attribution2.setStyleSheet("#attribution2 { " +
                           "background-color: transparent; color: " +
                           Config.textcolor +  
                           "; font-size: " +
                           str(int(12 * xscale * Config.fontmult)) +
                           "px; " +
                           Config.fontattr +
                           "}")
attribution2.setAlignment(Qt.AlignTop)
attribution2.setGeometry(int(6 * xscale), \
    int(880 * yscale), int(150 * xscale), 100)  

#                         Иконка на 2 странице
wxicon2 = QtWidgets.QLabel(frame2)
wxicon2.setObjectName("wxicon2")
wxicon2.setStyleSheet("#wxicon2 { background-color: transparent; }")
wxicon2.setGeometry(int(0 * xscale),  \
    int(750 * yscale), int(150 * xscale), int(150 * yscale))

#                         Текст состояние погоды 
ypos += 130
wxdesc = QtWidgets.QLabel(foreGround)
wxdesc.setObjectName("wxdesc")
wxdesc.setStyleSheet("#wxdesc { background-color: transparent; color: " +
                     Config.textcolorWeather + 
                     "; font-size: " +
                     str(int(30 * xscale)) +
                     "px; " +
                     Config.fontattr +
                     "}")
wxdesc.setAlignment(Qt.AlignLeft | Qt.AlignTop)  
wxdesc.setGeometry(int(3 * xscale), int(ypos * yscale), int(600 * xscale), 800)  

#                         Текст состояние погоды на 2 странице
wxdesc2 = QtWidgets.QLabel(frame2)
wxdesc2.setObjectName("wxdesc2")
wxdesc2.setStyleSheet("#wxdesc2 { background-color: transparent; color: " +
                      Config.textcolorWeather2 +  
                      "; font-size: " +
                      str(int(50 * xscale * Config.fontmult)) +
                      "px; " +
                      Config.fontattr +
                      "}")
wxdesc2.setAlignment(Qt.AlignLeft | Qt.AlignTop)
wxdesc2.setGeometry(int(150 * xscale), int(845 * yscale), int(900 * xscale), 100) 

#                             Температура слева вверху
ypos += 25
temper = QtWidgets.QLabel(foreGround)
temper.setObjectName("temper")
temper.setStyleSheet("#temper { background-color: transparent; color: " + 
                     Config.textcolorTemper +   
                     "; font-size: " +
                     str(int(70 * xscale * Config.fontmult)) +
                     "px; " +
                     Config.fontattr +
                     "}")
temper.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
temper.setGeometry(int(3 * xscale), int(ypos * yscale), int(300 * xscale), int(100 * yscale))

#                             Температура на 2 странице
temper2 = QtWidgets.QLabel(frame2)
temper2.setObjectName("temper2")
temper2.setStyleSheet("#temper2 { background-color: transparent; color: " +  
                      Config.textcolorTemper2 +  
                      "; font-size: " +
                      str(int(70 * xscale * Config.fontmult)) +
                      "px; " +
                      Config.fontattr +  
                      "}")
temper2.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
temper2.setGeometry(int(125 * xscale), int(780 * yscale), int(300 * xscale), 100) 

#                             Строка слева Давление:
ypos += 80
press = QtWidgets.QLabel(foreGround)
press.setObjectName("press")
press.setStyleSheet("#press { background-color: transparent; color: " +
                    Config.textcolorPress +  
                    "; font-size: " +
                    str(int(26 * xscale * Config.fontmult)) +  
                    "px; " +
                    Config.fontattr +
                    "}")
press.setAlignment(Qt.AlignLeft | Qt.AlignTop) 
press.setGeometry(int(10 * xscale), int(ypos * yscale), int(400 * xscale), 100)  

#                             Строка слева Влажность:
ypos += 30
humidity = QtWidgets.QLabel(foreGround)
humidity.setObjectName("humidity")
humidity.setStyleSheet("#humidity { background-color: transparent; color: " +  
                       Config.textcolorHumidity +  #                             Цвет
                       "; font-size: " +
                       str(int(25 * xscale * Config.fontmult)) +
                       "px; " +
                       Config.fontattr +
                       "}")
humidity.setAlignment(Qt.AlignLeft | Qt.AlignTop)
humidity.setGeometry(int(10 * xscale), int(ypos * yscale), int(500 * xscale), 100)

#                              Строка слева Ветер:
ypos += 30
wind = QtWidgets.QLabel(foreGround)
wind.setObjectName("wind")
wind.setStyleSheet("#wind { background-color: transparent; color: " +  # Ветер
                   Config.textcolor +
                   "; font-size: " +
                   str(int(21 * xscale * Config.fontmult)) +  #        Шрифт
                   "px; " +
                   Config.fontattr +
                   "}")
wind.setAlignment(Qt.AlignLeft | Qt.AlignTop)      
wind.setGeometry(int(10 * xscale), int(ypos * yscale), int(500 * xscale), 100)  

#                              Строка слева По Ощущению:
ypos += 20
feelslike = QtWidgets.QLabel(foreGround)
feelslike.setObjectName("feelslike")
feelslike.setStyleSheet("#feelslike { background-color: transparent; color: " +  
                        Config.textcolor +
                        "; font-size: " +
                        str(int(21 * xscale * Config.fontmult)) +  #         Шрифт
                        "px; " +
                        Config.fontattr +
                        "}")
feelslike.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
feelslike.setGeometry(int(3 * xscale), int(ypos * yscale), int(300 * xscale), 100)

#                              строка слева Данные на:
ypos += 20
wdate = QtWidgets.QLabel(foreGround)
wdate.setObjectName("wdate")
wdate.setStyleSheet("#wdate { background-color: transparent; color: " +  
                    Config.textcolor +
                    "; font-size: " +
                    str(int(15 * xscale * Config.fontmult)) +
                    "px; " +
                    Config.fontattr +
                    "}")
wdate.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
wdate.setGeometry(int(3 * xscale), int(ypos * yscale), int(300 * xscale), 100)

#                               Нижняя строка. Восход Заход, фазы луны
bottom = QtWidgets.QLabel(foreGround)
bottom.setObjectName("bottom")
bottom.setStyleSheet("#bottom { font-family:sans-serif; color: " +  
                     Config.textcolorBottom +  #                        Цвет
                     "; background-color: transparent; font-size: " +
                     str(int(30 * xscale * Config.fontmult)) +  #       Шрифт
                     "px; " +
                     Config.fontattr +
                     "}")
bottom.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
bottom.setGeometry(0, int(height - 50 * yscale), width, int(50 * yscale))

#                               Температура строка внизу
temp = QtWidgets.QLabel(foreGround)
temp.setObjectName("temp")
temp.setStyleSheet("#temp { font-family:sans-serif; color: " +
                   Config.textcolorTempInDoor +
                   "; background-color: transparent; font-size: " +
                   str(int(30 * xscale * Config.fontmult)) +
                   "px; " +
                   Config.fontattr +
                   "}")
temp.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
temp.setGeometry(0, int(height - 100 * yscale), width, int(50 * yscale))



#                              строка Видимость, Облачность, УФ индекс
ypos += 450
ccfields = QtWidgets.QLabel(foreGround)
ccfields.setObjectName("ccfields")
ccfields.setStyleSheet("#ccfields { background-color: transparent; color: " +
                    Config.colorCCfields + 
                    "; font-size: " +
                    str(int(29 * xscale * Config.fontmult)) +
                    "px; " +
                    Config.fontattr +
                    "}")
ccfields.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
ccfields.setGeometry(0, int(height - 150 * yscale), width, int(50 * yscale))
ccfields.raise_()

#                              Прогноз в столбике
forecast = []
for i in range(0, 9):
    lab = QtWidgets.QLabel(foreGround)
    lab.setObjectName("forecast" + str(i))
    lab.setStyleSheet("QWidget { background-color: transparent; color: " +
                      Config.textcolor +
                      "; font-size: " +
                      str(int(20 * xscale * Config.fontmult)) +
                      "px; " +
                      Config.fontattr +
                      "}")
    lab.setGeometry(int(1137 * xscale), int(i * 100 * yscale), int(300 * xscale), int(100 * yscale))
    lab.stackUnder(datex)

#                               Иконка справа в столбце
    icon = QtWidgets.QLabel(lab)
    icon.setStyleSheet("#icon { background-color: transparent; }")
    icon.setGeometry(10, 10, int(65 * xscale), int(65 * yscale))  
    icon.setObjectName("icon")

#                               Текст в Столбике
    wx = QtWidgets.QLabel(lab)
    wx.setStyleSheet("#wx { background-color: transparent; }")
    wx.setGeometry(int(100 * xscale), int(5 * yscale), int(200 * xscale), int(120 * yscale))
    wx.setAlignment(Qt.AlignLeft | Qt.AlignTop)  
    wx.setWordWrap(True)
    wx.setObjectName("wx")

#                               Дата в столбике
    day = QtWidgets.QLabel(lab)  
    day.setStyleSheet(Config.textcolorDayWeek) 
    day.setGeometry(int(10 * xscale), int(75 * yscale), int(250 * xscale), int(25 * yscale))
    day.setAlignment(Qt.AlignLeft | Qt.AlignBottom) 
    day.setObjectName("day")

    forecast.append(lab)

manager = QtNetwork.QNetworkAccessManager()

stimer = QtCore.QTimer()
stimer.singleShot(10, qtstart)

w.show()
w.showFullScreen()

sys.exit(app.exec_())
