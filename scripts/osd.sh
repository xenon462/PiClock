#! /bin/bash
#Убить процесс
killall -9 -q osd_cat &>/dev/null
killall -9 -q xosd &>/dev/null
# Увеличиваем уровень звука  на 1% и присваиваем 
#значение переменной volume

volume=$(amixer -c 0 sset PCM,0 \
$1 | grep "Left:" | awk '{print $4}' | tr -d '[]''%') 
# Выводим на экран 
osd_cat -b percentage -P $volume -p bottom -o 100 \
-A center -i 60 -s 0 -S white -d 3 \
-T $volume'%' -f "-adobe-helvetica-bold-*-*-34-240-*-*-*-*" \
-c white
