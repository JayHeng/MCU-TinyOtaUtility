#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2022 NXP
# All rights reserved.
# 
# SPDX-License-Identifier: BSD-3-Clause

import sys
import os
import serial.tools.list_ports
from PyQt5.Qt import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from . import uidef
from . import uilang
from . import uivar
sys.path.append(os.path.abspath(".."))
from win import tinyOtaWin
from utils import misc

s_serialPort = serial.Serial()

class tinyOtaUi(QMainWindow, tinyOtaWin.Ui_tinyOtaWin):

    def __init__(self, parent=None):
        super(tinyOtaUi, self).__init__(parent)
        self.setupUi(self)

        self.exeBinRoot = os.getcwd()
        self.exeTopRoot = os.path.dirname(self.exeBinRoot)
        exeMainFile = os.path.join(self.exeTopRoot, 'src', 'main.py')
        if not os.path.isfile(exeMainFile):
            self.exeTopRoot = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        uivar.setRuntimeSettings(None, self.exeTopRoot)
        uivar.initVar(os.path.join(self.exeTopRoot, 'bin', 'ota_settings.json'))
        toolCommDict = uivar.getAdvancedSettings(uidef.kAdvancedSettings_Tool)
        self.toolCommDict = toolCommDict.copy()

        self.mcuDevice = None
        self._initTargetSetupValue()
        self.setTargetSetupValue()
        self.initFuncUi()

    def initFuncUi( self ):
        self.uartComPort = None
        self.uartBaudrate = None
        self.setPortSetupValue()

    def showAboutMessage( self, myTitle, myContent):
        QMessageBox.about(self, myTitle, myContent )

    def showInfoMessage( self, myTitle, myContent):
        QMessageBox.information(self, myTitle, myContent )

    def adjustPortSetupValue( self ):
        # Auto detect available ports
        comports = list(serial.tools.list_ports.comports())
        ports = [None] * len(comports)
        for i in range(len(comports)):
            comport = list(comports[i])
            ports[i] = comport[0]
        lastPort = self.comboBox_comPortVid.currentText()
        lastBaud = self.comboBox_baudratePid.currentText()
        self.comboBox_comPortVid.clear()
        self.comboBox_comPortVid.addItems(ports)
        if lastPort in ports:
            self.comboBox_comPortVid.setCurrentIndex(self.comboBox_comPortVid.findText(lastPort))
        else:
            self.comboBox_comPortVid.setCurrentIndex(0)
        baudItems = ['115200']
        self.comboBox_baudratePid.clear()
        self.comboBox_baudratePid.addItems(baudItems)
        if lastBaud in baudItems:
            self.comboBox_baudratePid.setCurrentIndex(self.comboBox_baudratePid.findText(lastBaud))
        else:
            self.comboBox_baudratePid.setCurrentIndex(0)

    def _initTargetSetupValue( self ):
        self.comboBox_mcuDevice.clear()
        self.comboBox_mcuDevice.addItems(uidef.kMcuDevice_v1_0)
        self.comboBox_mcuDevice.setCurrentIndex(self.toolCommDict['mcuDevice'])

    def setTargetSetupValue( self ):
        self.mcuDevice = self.comboBox_mcuDevice.currentText()
        self.toolCommDict['mcuDevice'] = self.comboBox_mcuDevice.currentIndex()

    def updateTargetSetupValue( self ):
        uivar.setAdvancedSettings(uidef.kAdvancedSettings_Tool, self.toolCommDict)
        return True

    def updatePortSetupValue( self ):
        self.uartComPort = self.comboBox_comPortVid.currentText()
        self.uartBaudrate = self.comboBox_baudratePid.currentText()

    def setPortSetupValue( self ):
        self.adjustPortSetupValue()
        self.updatePortSetupValue()


