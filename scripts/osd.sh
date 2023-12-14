#! /bin/bash
volume=$(amixer sset 'Master',0 \
$1 | grep "Left:" | awk '{print $5}' | tr -d '[]''%')
killall -9 -q osd_cat &>/dev/null # xosd &>/dev/null
# Выводим на экран 
DISPLAY=:0.0
osd_cat -b percentage -P $volume -p bottom -o 150 \
-A center -i 60 -s 0 -S white -d 4 \
-T $volume'%' -f "-adobe-helvetica-bold-*-*-34-240-*-*-*-*" \
-c white
