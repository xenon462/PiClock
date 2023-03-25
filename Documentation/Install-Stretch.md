# Установка RpiClock
## для Raspbian Stretch

### Установить **Raspbian Stretch OS with desktop** на SD карту: [Скачать: 2019-04-08-raspbian-stretch.zip](https://downloads.raspberrypi.org/raspbian/images/raspbian-2019-04-09/)
- Создать пустой текстовый файл в корне SD карты с именем: `ssh`
- Создать текстовый файл `wpa_supplicant.conf`   в корне SD карты и добавить эти строки:
```
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev  
update_config=1  
country=RU  
network={  
ssid="Asus-2.4Ghz"  
psk="1bt4Y284"  
key_mgmt=WPA-PSK  
}
```
### Загрузить Raspberry pi и изменить настройки: `sudo raspi-config`

 -  **Change User Password => Enter new UNIX password**
 -  **Network Options => Hostname => PiClock**	
 -  **Boot Options => Desktop / CLI => Desktop Autologin** 
 -  **Boot Options => Splash Screen => NO** 	
 -  **Localisation Options => Change Locale => ru_RU.UTF-8 UTF-8**
 -  **Localisation Options => Change Timezone => Europe => Moscow**
 -  **Advanced Options => Expand Filesystem** 
 -  **Update**  
 -  **Finish  =>  Yes**
 
Oбновить информацию обо всех пакетах: 

```    
sudo apt-get update 
```
Для  работы драйвера светодиодов *rpi-ws281x* и звука внести изменения в файл. 
``` 
 sudo nano /etc/modprobe.d/snd-blacklist.conf 
```
 добавить строку: 
```
blacklist snd_bcm2835
```

открыть файл настроек и внести изменения.
```
sudo nano /boot/config.txt`
```
удалить строку:  `dtparam=audio=on`
добавить эти строки:
```
dtparam=audio=off 
dtoverlay=gpio-ir,gpio_pin=3
dtoverlay=w1-gpio,gpiopin=4
```

### Настроить звук.
Создать файл
```
sudo nano /etc/asound.conf`
```
со следующим содержимым:
```
pcm.sftvol {
type softvol
slave.pcm "plughw:0"
control {
name "PCM"
card 0
}
}
pcm.!default {
type plug
slave.pcm "sftvol"
}
```  

перезагрузить
`sudo systemctl reboot`

### Проверить звук
`speaker-test -D default -c 2 -twav`

Уровень громкости:
`alsamixer`


### Устанавить qt5 для Python    

`sudo apt-get install python3-pyqt5 -y`


### Установить PiClock

не root
```
git clone https://github.com/xenon462/PiClock.git`
```

для использования кнопок выполнить:
`cd PiClock/Button`
`make gpio-keys`
`cd ../..`

### Установить библиотеку rpi_ws281x

[официальный дистрибутив Python библиотеки ws281x.](https://github.com/rpi-ws281x/rpi-ws281x-python)

```
sudo pip3 install rpi_ws281x && sudo reboot`
```

### Проверить работу светодиодной ленты:
```
cd PiClock/Leds && sudo python3 NeoAmbi.py && cd
```

### Установить библиотеки Python

`sudo su`

`pip3 install --upgrade pip && pip3 install python-dateutil --upgrade && pip3 install tzlocal --upgrade && reboot`

### Установить программу для отключения указателя мыши, когда нет активности
```
sudo apt-get install unclutter`
```

### Установить драйвер датчика DS18b20 для измерения температуры внутри помещения

[страница проекта w1thermsensor:](https://github.com/timofurrer/w1thermsensor)

 
`sudo pip3 install w1thermsensor && sudo reboot`

### Показать HWID подключенных датчиков: 
`w1thermsensor ls`

### Показать температуру датчика №1
`w1thermsensor get 1`

### В файле Config изменить серийный номер (HWID) датчика: sensds18b20 = 'xxxxxxx'

`nano PiClock/Clock/Config.py`

### Установить драйвер Lirc для работы ИК пульта

``` 
sudo apt-get install lirc -y
```

### Cкопировать файл конфигурации пульта HX1838 17keys
```
sudo cp PiClock/IR/HX1838.conf /etc/lirc/lircd.conf.d
```

### Cкопировать файл irexec.lircrc
```
sudo cp PiClock/IR/irexec.lircrc /etc/lirc/irexec.lircrc
```
### Cкопировать файл настроек
```
sudo cp PiClock/IR/lirc_options.conf /etc/lirc/lirc_options.conf
```

в файле lirc_options.conf дожны быть такие строки:
`sudo nano /etc/lirc/lirc_options.conf`
   
driver = default
device = /dev/lirc0


### Запустить сервис
```
sudo systemctl start irexec.service
```

### Включить автозагрузку сервиса
```
sudo systemctl enable irexec
```

### Исправить ошибку системы
Пульт выдаёт бесконечное количество команд. Для нормальной работы пульта отредактировать службу, добавить параметр.

`sudo nano /lib/systemd/system/lircd-uinput.service`

 изменить эту строку
`ExecStart=/usr/sbin/lircd-uinput` 

 вот так
`ExecStart=/usr/sbin/lircd-uinput --add-release-events`

Перезагрузить:
```
sudo systemctl reboot
```
### Проверить пульт

`irw`

### Установить пакет для показа сообщений на экране 

`sudo apt-get install xosd-bin -y`

### Установить шрифты
```
sudo apt-get install t1-xfree86-nonfree ttf-xfree86-nonfree ttf-xfree86-nonfree-syriac xfonts-75dpi xfonts-100dpi -y
```

### Перезагрузить
```
sudo systemctl reboot
```

### Проверить работу программы вывода сообщений на экран 
`export DISPLAY=:0.0`
`echo "hello world" | osd_cat -A center -p bottom -f -*-*-bold-*-*-*-36-120-*-*-*-*-*-* -cgreen -s 5`


### Установить права на выполнение
`sudo chmod a+x PiClock/scripts/osd.sh`


### Установить аудио плеер mpg123 
```
sudo apt-get install mpg123 -y
```
Дорожное радио Ялта
`mpg123 -q http://109.200.130.38:8000/dorozh-yalta`
Dance 
`mpg123 -q http://stream.nonstopplay.co.uk/nsp-128k-mp3`

громкость:
`alsamixer`

### Установить Bluetooth


### Настройка API-ключей для PiClock
Получить ключи:    
[mapbox.com](https://www.mapbox.com/)   Для загрузки карты    
[openweathermap.org](https://openweathermap.org/) Погода    
[climacell = tomorrow.io](https://www.tomorrow.io/) Другая погода    
[thingspeak.com](https://thingspeak.com/) для датчика температуры    
### Создать файл ApiKeys.py и записать в него ключи


`cd PiClock/Clock`
`cp ApiKeys-example.py ApiKeys.py`

### Cохранить ключи в файл:
```
nano ApiKeys.py 
```

### Настройка:
```
nano Config.py
```

### Запустить PiClock
```
cd && sh PiClock/startup.sh -n -s
```

### Для запуска программ в автоматическом режиме поместить эти строки в планировщик заданий
```
`crontab -e
```

### добавить строки:
```
@reboot sh /home/pi/PiClock/startup.sh
# Прогноз голосом в 7часов 20 минут каждый будний день
15 7 * * 1-5 amixer cset numid=1 -- 180 >/dev/null 2>&1 && python3 PiClock/scripts/meteonova.py
# Сигнал зуммер каждый час с 8 до 17 часов в будние дни.
0 8-17 * * 1-5 python PiClock/scripts/buzzer.py
# Будильник 'Рассвет' в 6 часов 20 минут в будние дни
20 6 * * 1-5 sudo python3  /home/pi/PiClock/Leds/dawn.py; sudo python3  /home/pi/PiClock/Leds/all_leds_off.py

```

### перезагрузить
`sudo reboot

### Обновление программы из GitHub

удалить каталог:
`rm -fr PiClock`

не root
`git clone https://github.com/xenon462/PiClock.git`

для кнопок выполнить
`cd PiClock/Button`  
`make gpio-keys`
`cd ../..`

 Cделать файл исполняемым
`sudo chmod u+x PiClock/scripts/osd.sh`

Создать файл ApiKeys.py и записать в него ключи

`cd PiClock/Clock` 
`cp ApiKeys-example.py ApiKeys.py`

сохранить ключи в файл:

`nano ApiKeys.py` 

скопировать файл конфигурации пульта HX1838 17keys

`cd PiClock`
`sudo cp IR/HX1838.conf /etc/lirc/lircd.conf.d/`

 
### ПУЛЬТ HX1838
 < > Карта
 ^v Громкость
 1 Красный  
 2 Оранжевый
 3 Желтый
 4 Зеленый
 5 Голубой
 6 Синий
 7 Фиолетовый
 8 Белый тусклый
 9 Белый
 0 Метеонова 
     # Радуга
     * Выключить Leds
 ОК выкл. звук

