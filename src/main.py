#! /usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import os
from PyQt5.Qt import *
from win import tinyOtaWin

class tinyOtaMain(QMainWindow, tinyOtaWin.Ui_tinyOtaWin):

    def __init__(self, parent=None):
        super(tinyOtaMain, self).__init__(parent)
        self.setupUi(self)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = tinyOtaMain()
    mainWin.setWindowTitle(u"MCU Tiny OTA Utility v1.0")
    mainWin.show()

    sys.exit(app.exec_())

