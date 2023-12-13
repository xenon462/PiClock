# Установка RpiClock  

### Для Raspberry Pi OS (Legacy, 64-bit) with desktop. Debian version: 11 (bullseye)  

### 1. Установить ОС: [2023-05-03-bullseye](https://downloads.raspberrypi.com/raspios_oldstable_armhf/images/raspios_oldstable_armhf-2023-10-10/2023-05-03-raspios-bullseye-armhf.img.xz) с помощью [Raspberry Pi Imager](https://downloads.raspberrypi.org/imager/imager_latest.exe) на SD карту  

#### В настройках Raspberry pi imager Изменить параметры установки ОС

- Имя хоста: PiClock  
- Указать имя пользователя и пароль
- Настроить Wi-Fi
- Указать параметры региона
- Включить SSH
- Записать ОС на SD карту  

Проверить версию ОС можно командой: `cat /etc/os-release`

### 2. Первая загрузка и настройка:

`sudo raspi-config`

- **System Options ⇒  Boot/Auto Login ⇒ Desktop Autologin**
- **Localisation Options ⇒ Locale ⇒ ru_RU.UTF-8 UTF-8**
- **Advanced Options ⇒ Expand Filesystem**

#### Или создать файл для изменения настроек конфигурации Raspberry pi 
```
sudo nano configure.sh
```   
со следующим содержимым
```
#! /bin/bash
sudo raspi-config nonint do_change_locale ru_RU.UTF-8 UTF-8;
echo "\033[33m--- 1. Изменён язык системы на ru_RU.UTF-8";
sudo raspi-config nonint do_expand_rootfs;
echo "\033[33m--- 2. Выполнено  расширение системы на весь размер SD карты ";
sudo apt-get update;
echo "\033[33m--- 3. Обновление выполнено";
sudo apt-get install python3-pyqt5 -y;
echo "\033[33m--- 4. pyqt5 установлен ";
sudo sh -c "echo '[SeatDefaults]\nxserver-command=X -s 0 -dpms' >> /etc/lightdm/lightdm.conf";
echo "\033[33m--- 5. Отключение заставки выполнено";
echo "\033[33m--- 6. Настройка конфигурации Raspberry завершена";
echo "\033[91m--- 7. Для перезагрузки нажмите Enter"
read -p "" y
echo "\033[93m--- Перезагрузка...";
sleep 2;
sudo systemctl reboot;
exit 0
```

и выполнить командой  

```
sudo sh configure.sh
```

### 3. Настроить звук.

Для работы звука и драйвера светодиодов *rpi-ws281x*   
добавить строку ***blacklist snd_bcm2835*** в файл ***/etc/modprobe.d/snd-blacklist.conf***  
командой:
``` 
sudo sh  -c "echo 'blacklist snd_bcm2835' >> /etc/modprobe.d/snd-blacklist.conf"
```

открыть файл настроек и внести изменения.

```
sudo nano /boot/config.txt
```

Удалить строку: `dtparam=audio=on`  
Добавить эти строки:  

```
dtparam=audio=off
dtoverlay=gpio-ir,gpio_pin=3
dtoverlay=w1-gpio,gpiopin=4
```

Сохранить и выйти.  
#### Создать файл.

```
sudo nano /etc/asound.conf
```

со следующим содержимым:

```
pcm.!default {
  type hw card 0
}
ctl.!default {
  type hw card 0
}
```

#### Перезагрузить.
```
sudo systemctl reboot
```

#### Проверить звук.

```
speaker-test -D default -c 2 -twav
```

#### Уровень громкости: `alsamixer`

### 4. Установить PiClock

не root

```
git clone https://github.com/xenon462/PiClock.git
```

#### для использования кнопок выполнить:  
```
cd PiClock/Button && make gpio-keys && cd ../..
```

### 5. Установить библиотеку rpi_ws281x

[Установка Python библиотеки NeoPixel ](https://learn.adafruit.com/neopixels-on-raspberry-pi/python-usage)

```
sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel && sudo reboot
```

#### Проверить работу светодиодной ленты:

```
cd PiClock/Leds && sudo python3 NeoAmbi.py && cd
```

### 6. Установить библиотеки Python

```
python3 -m pip install --upgrade pip
python3 -m pip install python-dateutil --upgrade
python3 -m pip install python-metar --upgrade
python3 -m pip install pytz --upgrade
python3 -m pip install timezonefinder --upgrade
python3 -m pip install tzlocal --upgrade

```
или создать bash скрипт 
```
sudo nano libPy.sh
```
со следующим содержимым
```
#! /bin/bash
python3 -m pip install --upgrade pip;
echo "\033[92m--- 1. Обновление pip выполнено успешно";
python3 -m pip install python-dateutil --upgrade;
echo "\033[92m--- 2. Установка dateutil выполнено успешно ";
python3 -m pip install python-metar --upgrade;
echo "\033[92m--- 3. Установка metar выполнено успешно ";
python3 -m pip install pytz --upgrade;
echo "\033[92m--- 4. Установка pytz выполнено успешно ";
python3 -m pip install timezonefinder --upgrade;
echo "\033[92m--- 5. Установка timezonefinder выполнено успешно ";
python3 -m pip install tzlocal --upgrade;
echo "\033[92m--- 6. Установка tzlocal выполнено успешно ";
echo "\033[92m--- 7. Установка библиотек Python завершена ";
exit 0

```

и установить библиотеки командой  

```
sudo sh libPy.sh
```

### 7. Установить программу для отключения указателя мыши, когда нет активности

```
sudo apt-get install unclutter -y
```

### 8. Установить [*драйвер датчика DS18b20*](https://github.com/timofurrer/w1thermsensor) для измерения температуры внутри помещения

```
sudo pip3 install w1thermsensor && sudo reboot
```

#### Показать HWID (Hardware ID) подключенных датчиков:

```
w1thermsensor ls
```

#### Показать температуру датчика №1

```
w1thermsensor get 1
```

#### В файле Config изменить серийный номер (HWID) датчика: sensds18b20 = 'xxxxxxx'

```
nano PiClock/Clock/Config.py
```

### 9. Установить драйвер Lirc для работы ИК пульта

``` 
sudo apt-get install lirc -y
```

#### Cкопировать файл конфигурации пульта HX1838 17keys

```
sudo cp PiClock/IR/HX1838.conf /etc/lirc/lircd.conf.d
```

#### Cкопировать файл irexec.lircrc

```
sudo cp PiClock/IR/irexec.lircrc /etc/lirc/irexec.lircrc
```

#### Открыть файл настроек ***lirc_options.conf***  

```
sudo nano /etc/lirc/lirc_options.conf
```

##### изменить строки вот так:

```
driver   = default
device   = /dev/lirc0
```

#### Включить автозагрузку сервиса _irexec_ от имени пользователя _pi_
* Создать директорию _autostart_
```
mkdir /home/pi/.config/autostart
```
* Скопировать файл _irexec.desktop_ в директорию _autostart_
```
sudo cp /usr/share/lirc/contrib/irexec.desktop /home/pi/.config/autostart
```

* Сменить владельца
```
sudo chown pi /home/pi/.config/autostart/irexec.desktop
```

* Открыть файл
```
nano /home/pi/.config/autostart/irexec.desktop
```
* Удалить верхнюю строку ***; Drop in ~/.config/autostart to create a session irexec service***
* Изменить строку ***Exec=run-irexec*** на: 
```
Exec=/usr/bin/irexec /etc/lirc/irexec.lircrc
```

* Перезагрузить:

```
sudo systemctl reboot
```

#### Проверить пульт

`irw`

### 10. Установить пакет для показа сообщений на экране

```
sudo apt-get install xosd-bin -y
```

#### Установить шрифты

```
sudo apt-get install xfonts-100dpi -y && sudo systemctl reboot
```

#### Проверить работу программы вывода сообщений на экран

```
export DISPLAY=:0.0
```

```
echo "hello world" | osd_cat -A center -p bottom -f -*-*-bold-*-*-*-36-120-*-*-*-*-*-* -cgreen -s 5
```

#### Установить права на выполнение скрипта osd.sh

```
sudo chmod a+x PiClock/scripts/osd.sh
```

### 11. Установить аудио плеер mpg123

```
sudo apt-get install mpg123 -y
```

#### Radio Dance

```
mpg123 -q http://stream.nonstopplay.co.uk/nsp-128k-mp3
```

#### громкость:

```
alsamixer
```

### 12. Настройка API-ключей для PiClock

#### Получить ключи:  
[mapbox.com](https://www.mapbox.com/)   Для загрузки карты  
[openweathermap.org](https://openweathermap.org/) Погода  
[climacell = tomorrow.io](https://www.tomorrow.io/) Другая погода  
[thingspeak.com](https://thingspeak.com/) для датчика температуры

#### Создать файл ApiKeys и записать в него ключи

```
cd PiClock/Clock
```

```
cp ApiKeys-example.py ApiKeys.py
```

#### Cохранить ключи в файл:

```
nano ApiKeys.py
```

### 13. Настройка PiClock:

```
nano Config.py
```

### 14. Запустить PiClock

```
cd && sh PiClock/startup.sh -n -s
```

#### Для запуска программ в автоматическом режиме поместить эти строки в планировщик заданий

```
crontab -e
```

#### добавить строки:

```
@reboot sh /home/pi/PiClock/startup.sh
# Прогноз голосом в 7часов 20 минут каждый будний день
15 7 * * 1-5 amixer cset numid=1 -- 180 >/dev/null 2>&1 && python3 PiClock/scripts/meteonova.py
# Сигнал зуммер каждый час с 8 до 17 часов в будние дни.
0 8-17 * * 1-5 python PiClock/scripts/buzzer.py
# Будильник 'Рассвет' в 6 часов 20 минут в будние дни
20 6 * * 1-5 sudo python3  /home/pi/PiClock/Leds/dawn.py; sudo python3  /home/pi/PiClock/Leds/all_leds_off.py

```

### 15. Настроить Raspberry pi как Bluetooth колонку

#### Установить:

```
sudo apt install pulseaudio-module-bluetooth
```

#### добавить pi пользователя в группу Bluetooth

```
sudo usermod -a -G bluetooth pi
```

#### Перезагрузить

```
sudo reboot
```

#### запустить PulseAudio

```
systemctl --user start pulseaudio
```

#### запустить интерфейс bluetoothctl.

```
bluetoothctl
```

#### Включить Bluetooth на смартфоне.  
#### Запустить сканирование Bluetooth устройств.

```
scan on
```

#### Скопировать MAC адрес найденного смартфона.  
#### Остановить сканирование.

```
scan off
```

#### Соединить и доверить.

```
pair 04:B4:29:FE:EB:52
```

```
trust 04:B4:29:FE:EB:52
```

#### для подключения смартфона ввести команду

```
connect 04:B4:29:FE:EB:52
```

#### Выход

```
exit
```

#### перезагрузить

```
sudo reboot
```

### Обновление программы из GitHub

удалить каталог:

```
sudo rm -fr PiClock
```

не root

```
git clone https://github.com/xenon462/PiClock.git
```

для кнопок выполнить

```
cd PiClock/Button  
```

```
make gpio-keys  
```

```
cd ../..
```

Cделать файл исполняемым.

```
sudo chmod u+x PiClock/scripts/osd.sh
```

Создать файл ApiKeys.py и записать в него ключи.

```
cd PiClock/Clock  
```

```
cp ApiKeys-example.py ApiKeys.py
```

сохранить ключи в файл:

```
nano ApiKeys.py
```

скопировать файл конфигурации пульта HX1838 17keys

```
cd PiClock  
```

```
sudo cp IR/HX1838.conf /etc/lirc/lircd.conf.d/
```

### ПУЛЬТ HX1838

```
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
```