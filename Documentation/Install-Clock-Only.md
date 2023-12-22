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
sudo apt-get upgrade -y;
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

#### и выполнить командой  

```
sudo sh configure.sh
```

#### открыть файл настроек и внести изменения.

```
sudo nano /boot/config.txt
```

#### Добавить строки:  

```
dtoverlay=w1-gpio,gpiopin=4
# Disable Bluetooth
dtoverlay=disable-bt
```

#### Сохранить и выйти.  

### 3. Установить PiClock

не root

```
git clone https://github.com/xenon462/PiClock.git
```

### 4. Установить библиотеки Python

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
sh libPy.sh
```

### 5. Установить программу для отключения указателя мыши, когда нет активности

```
sudo apt-get install unclutter -y
```

### 6. Установить [*драйвер датчика DS18b20*](https://github.com/timofurrer/w1thermsensor) для измерения температуры внутри помещения

```
python3 -m pip install w1thermsensor
```
#### Перезагрузить
```
sudo systemctl reboot
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

### 7. Настройка API-ключей для PiClock

#### Получить ключи:  
[mapbox.com](https://www.mapbox.com/)   Для загрузки карты  
[openweathermap.org](https://openweathermap.org/) Погода  
[climacell = tomorrow.io](https://www.tomorrow.io/) Другая погода  
[thingspeak.com](https://thingspeak.com/) для датчика температуры

#### Создать файл ApiKeys и записать в него ключи

```
cp PiClock/Clock/ApiKeys-example.py PiClock/Clock/ApiKeys.py && nano PiClock/Clock/ApiKeys.py
```

### 8. Настройка PiClock:

```
nano PiClock/Clock/Config.py
```

### 9. Запустить PiClock

```
sh PiClock/startup.sh -n -s
```

#### Для запуска программ в автоматическом режиме открыть планировщик заданий

```
crontab -e
```

#### Добавить строки:

```
@reboot sh /home/pi/PiClock/startup.sh
0 22 * * * python /home/pi/PiClock/scripts/display-off.py
20 6 * * 1-5 python /home/pi/PiClock/scripts/display-on.py
20 7 * * 6-7 python /home/pi/PiClock/scripts/display-on.py
```