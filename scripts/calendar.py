from PyQt5 import QtCore, QtWidgets

import sys

StyleSheet = ('\n'
              '\n'
              '#qt_calendar_navigationbar {\n'
              '    background-color: #232732;\n'  # Верняя навигат панель**********************
              '    min-height: 60px;\n'  # высота верхней строки год месяц********************
              '    font: bold 36px;\n'  # Шрифт год месяц ************************************
              '    \n'
              '}\n'
              '\n'
              '\n'
              '#qt_calendar_prevmonth, #qt_calendar_nextmonth {\n'
              #              "    border: none; \n"
              #              "    margin-top: 64px;\n"
              #              "    color: blue;\n"
              #              "    min-width: 36px;\n"
              #              "    max-width: 36px;\n"
              #              "    min-height: 36px;\n"
              #              "    max-height: 36px;\n"
              #              "    border-radius: 58px; \n"
              #              "    font-weight: bold; \n"
              '    qproperty-icon: none; \n'  # стрелки Месяц ***************************************
              '    background-color: transparent;\n'  # цвет стрелки месяца ************************
              '}\n'
              '\n'
              '#qt_calendar_yearbutton, #qt_calendar_monthbutton {\n'
              '    color: #72510c; \n'  # Месяц год  ***********************************************
              '    margin: 8px; \n'
              '    min-width: 32px; \n'
              '    border-radius: 5px; \n'
              '}\n'

              '#qt_calendar_calendarview {\n'
              '    outline: 0px; \n'
              '    selection-background-color: #bcb1ab; \n'  # цвет текущая дата********************
              '    background-color: #636164; \n'  # основной цвет ********************************
              '    font: bold 36px; \n'  # Шрифт в таблице календарь
              '    alternate-background-color: #dab202;\n'  # дни недели **************************** 
              '    selection-color: #1E90FF;\n'  # Выбранная дата *************************************

              '}\n'

              '#CalendarWidget QToolButton::menu-indicator {\n'
              '    image: none; \n'  # /* Удалите маленькую стрелку под выбором месяца !!! */
              '    subcontrol-position: right center; \n'
              '}\n'

              )


class UiMainwindow:

    def __init__(self):
        self.calendar = None
        self.centralwidget = None

    def setupui(self, mainwindow):
        # Заголовок окна
        mainwindow.setWindowTitle('КАЛЕНДАРЬ')
        # Размер окна
        mainwindow.resize(960, 600)

        self.centralwidget = QtWidgets.QWidget(mainwindow)
        mainwindow.setCentralWidget(self.centralwidget)
        # Создать виджет календарь

        self.calendar = QtWidgets.QCalendarWidget(self.centralwidget)

        self.calendar.setGridVisible(True)
        # Краткое написание дней # недели
        self.calendar.setHorizontalHeaderFormat(QtWidgets.QCalendarWidget.ShortDayNames)
        self.calendar.setVerticalHeaderFormat(QtWidgets.QCalendarWidget.NoVerticalHeader)
        # setGeometry for calendar
        self.calendar.setGeometry(QtCore.QRect(0, 0, 960, 600))

        mainwindow.setStyleSheet(StyleSheet)


app = QtWidgets.QApplication(sys.argv)
mymainwindow = QtWidgets.QMainWindow()
ui = UiMainwindow()
ui.setupui(mymainwindow)
mymainwindow.show()
sys.exit(app.exec_())
