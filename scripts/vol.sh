#!/bin/bash
killall -9 -q aosd_cat &>/dev/null
CURR_VOLUME=`/usr/bin/amixer sget 'Master',0 2>/dev/null | grep "Left:" | awk '{print $5}' | tr -d '[]''%'`

if [ "$CURR_VOLUME" != "0" ]
then
        echo "Громкость:" $CURR_VOLUME"%" | DISPLAY=:0.0 aosd_cat -n "Arial Black 48" -u 800 -o 100 -R CornflowerBlue -S none -f 0 -x 400 -y -230 -t 2 &
else
        echo "Звук Выкл." | DISPLAY=:0.0 aosd_cat -n "Arial Black 48" -u 1000 -o 100 -R red -S none -f 0 -x 500 -y -230 -t 2 &
fi