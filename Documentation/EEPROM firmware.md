### Прошивка EEPROM для HAT PiClock

CAT24C32WI-GT3 1.7~5.5V I2C 32Kb (4Kx8)

#### 1. Активировать видео ядро I2C путем добавления строки в начало файла ***config.txt***

```
sudo nano /boot/config.txt
```

Добавить строку

```
dtparam=i2c_vc=on
```

перезагрузить:

```
sudo reboot
```

#### 2. Установить EEPROM utils

```
git clone https://github.com/raspberrypi/hats.git
```

```
sudo apt-get install device-tree-compiler
```

Скомпилировать

```
cd hats/eepromutils
```

```
sudo make
```

Скопировать файлы прошивки в папку `pi`

```
cd /home/pi
```

```
git clone https://github.com/xenon462/eeprom-HAT-PiClock
```

Скопировать файлы в `hats/eepromutils`

```
cp -r eeprom-HAT-PiClock/. hats/eepromutils
```

#### 3. Замкнуть контакты на печатной плате для записи прошивки

Записать нули на EEPROM

```
cd hats/eepromutils
```

```
sudo ./eepflash.sh -w -f=blank.eep -t=24c32
```

Записать файл прошивки на eeprom

```
sudo ./eepflash.sh -w -f=PiClock.eep -t=24c32
```

перезагрузить

```
sudo reboot
```

Проверить работу прошивки:

```
cd /proc/device-tree/hat/ && more vendor
```

```
cd /proc/device-tree/hat/ && more product
```

Проверить наличие звуковой карты:

```
cat /proc/asound/cards
```

Проверить звук

```
speaker-test -D default -c 2 -twav
```

#### 4. Разомкнуть контакты на печатной плате для защиты от записи
