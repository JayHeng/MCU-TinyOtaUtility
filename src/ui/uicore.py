#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2022 NXP
# All rights reserved.
# 
# SPDX-License-Identifier: BSD-3-Clause

import sys
import os
import time
import serial.tools.list_ports
import pywinusb.hid
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

kRetryDetectTimes = 2

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
        self.isUartPortSelected = None
        self.isUsbhidPortSelected = None
        self.uartComPort = None
        self.uartBaudrate = None
        self.usbhidVid = None
        self.usbhidPid = None
        self.isUsbhidConnected = False
        self.usbhidToConnect = [None] * 2
        self._initPortSetupValue()

    def showAboutMessage( self, myTitle, myContent):
        QMessageBox.about(self, myTitle, myContent )

    def showInfoMessage( self, myTitle, myContent):
        QMessageBox.information(self, myTitle, myContent )

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

    def _initPortSetupValue( self ):
        if self.toolCommDict['isUsbhidPortSelected']:
            self.comboBox_interface.setCurrentIndex(1)
        else:
            self.comboBox_interface.setCurrentIndex(0)
        usbIdList = self.getUsbid()
        self.setPortSetupValue(uidef.kConnectStage_Rom, usbIdList)

    def task_doDetectUsbhid( self ):
        while True:
            if self.isUsbhidPortSelected:
                self._retryToDetectUsbhidDevice(False)
            time.sleep(1)

    def _retryToDetectUsbhidDevice( self, needToRetry = True ):
        usbVid = [None]
        usbPid = [None]
        self.isUsbhidConnected = False
        retryCnt = 1
        if needToRetry:
            retryCnt = kRetryDetectTimes
        while retryCnt > 0:
            # Auto detect USB-HID device
            hidFilter = pywinusb.hid.HidDeviceFilter(vendor_id = int(self.usbhidToConnect[0], 16), product_id = int(self.usbhidToConnect[1], 16))
            hidDevice = hidFilter.get_devices()
            if (len(hidDevice) > 0):
                self.isUsbhidConnected = True
                usbVid[0] = self.usbhidToConnect[0]
                usbPid[0] = self.usbhidToConnect[1]
                break
            retryCnt = retryCnt - 1
            if retryCnt != 0:
                time.sleep(2)
            else:
                usbVid[0] = 'N/A - Not Found'
                usbPid[0] = usbVid[0]
        if self.comboBox_comPortVid.currentText() != usbVid[0] or \
           self.comboBox_baudratePid.currentText() != usbPid[0]:
            self.comboBox_comPortVid.clear()
            self.comboBox_comPortVid.addItems(usbVid)
            self.comboBox_comPortVid.setCurrentIndex(0)
            self.comboBox_baudratePid.clear()
            self.comboBox_baudratePid.addItems(usbPid)
            self.comboBox_baudratePid.setCurrentIndex(0)

    def adjustPortSetupValue( self, connectStage=uidef.kConnectStage_Rom, usbIdList=[] ):
        self.isUartPortSelected = (self.comboBox_interface.currentIndex() == 0)
        self.isUsbhidPortSelected = (self.comboBox_interface.currentIndex() == 1)
        if self.isUartPortSelected:
            self.label_comPortVid.setText('COM Port:')
            self.label_baudratePid.setText('Baudrate:')
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
        elif self.isUsbhidPortSelected:
            self.label_comPortVid.setText('VID:')
            self.label_baudratePid.setText('PID:')
            if connectStage == uidef.kConnectStage_Rom:
                self.usbhidToConnect[0] = usbIdList[0]
                self.usbhidToConnect[1] = usbIdList[1]
                self._retryToDetectUsbhidDevice(False)
            elif connectStage == uidef.kConnectStage_Flashloader:
                self.usbhidToConnect[0] = usbIdList[2]
                self.usbhidToConnect[1] = usbIdList[3]
                self._retryToDetectUsbhidDevice(False)
            else:
                pass
        else:
            pass

    def setPortSetupValue( self, connectStage=uidef.kConnectStage_Rom, usbIdList=[], retryToDetectUsb=False, showError=False ):
        self.adjustPortSetupValue(connectStage, usbIdList)
        self.updatePortSetupValue(retryToDetectUsb, showError)

    def updatePortSetupValue( self, retryToDetectUsb=False, showError=False ):
        status = True
        self.isUartPortSelected = (self.comboBox_interface.currentIndex() == 0)
        self.isUsbhidPortSelected = (self.comboBox_interface.currentIndex() == 1)
        if self.isUartPortSelected:
            self.uartComPort = self.comboBox_comPortVid.currentText()
            self.uartBaudrate = self.comboBox_baudratePid.currentText()
        elif self.isUsbhidPortSelected:
            if self.isUsbhidConnected:
                self.usbhidVid = self.comboBox_comPortVid.currentText()
                self.usbhidPid = self.comboBox_baudratePid.currentText()
            else:
                self._retryToDetectUsbhidDevice(retryToDetectUsb)
                if not self.isUsbhidConnected:
                    status = False
                    if showError:
                        self.popupMsgBox('Cannnot find USB-HID device (vid=%s, pid=%s), Please connect USB cable to your board first!' %(self.usbhidToConnect[0], self.usbhidToConnect[1]))
                else:
                    self.usbhidVid = self.comboBox_comPortVid.currentText()
                    self.usbhidPid = self.comboBox_baudratePid.currentText()
        else:
            pass
        self.toolCommDict['isUsbhidPortSelected'] = self.isUsbhidPortSelected
        return status

    def popupMsgBox( self, msgStr, myTitle="Error"):
        QMessageBox.information(self, myTitle, msgStr )

