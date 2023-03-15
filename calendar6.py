import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCharFormat, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QCalendarWidget


class CalendarWidget(QCalendarWidget):
    def __init__(self, *args, **kwargs):
        super(CalendarWidget, self).__init__(*args, **kwargs)

        # Вертикальный заголовок.
        self.setVerticalHeaderFormat(self.NoVerticalHeader)

        # Изменить цвета субботы и воскресенья
        fmtSat = QTextCharFormat()
        fmtSat.setForeground(QBrush(QColor(187, 19, 25)))
        self.setWeekdayTextFormat(Qt.Saturday, fmtSat)
        fmtSun = QTextCharFormat()
        fmtSun.setForeground(QBrush(QColor(144, 5, 6)))
        self.setWeekdayTextFormat(Qt.Sunday, fmtSun)

Calendar_StyleSheet = '''
#qt_calendar_navigationbar {
    background-color: #232732;
    min-height: 60px;
    font: bold 36px;
}

/* Кнопка последнего месяца и кнопка следующего месяца */
#qt_calendar_prevmonth, #qt_calendar_nextmonth {
    qproperty-icon: none;
    background-color: transparent;
}

/*  год, месяц         */
#qt_calendar_yearbutton, #qt_calendar_monthbutton {
    color: #72510c;
    margin: 8px;
    min-width: 32px;
    border-radius: 5px;
}

CalendarWidget QToolButton::menu-indicator {
    image: none;       /* Удалить маленькую стрелку под выбором месяца */
    subcontrol-position: right center;               
}

#qt_calendar_calendarview {
    selection-background-color: #bcb1ab;  /* выбранная дата*/
    background-color: #636164;
    font: bold 40px;
    alternate-background-color: #dab202;
    selection-color: #1E90FF; /* цвет шрифта выбранной даты*/
}

'''

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(Calendar_StyleSheet)
    w = CalendarWidget()
    w.setWindowTitle('КАЛЕНДАРЬ')
    w.setGridVisible(True)
    w.resize(960, 600)
    w.show()
    sys.exit(app.exec_())