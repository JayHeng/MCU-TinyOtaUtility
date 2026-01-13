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

class TickWorker(QObject):
    tick = pyqtSignal()
    finished = pyqtSignal()
    def __init__(self, interval_sec=1):
        super().__init__()
        self._interval = max(1, int(interval_sec))
        self._stop = False
    @pyqtSlot()
    def run(self):
        try:
            while not self._stop:
                self.tick.emit()
                QThread.sleep(self._interval)
        finally:
            self.finished.emit()
    @pyqtSlot()
    def stop(self): self._stop = True

class tinyOtaUi(QMainWindow, tinyOtaWin.Ui_tinyOtaWin):

    def __init__(self, parent=None):
        super(tinyOtaUi, self).__init__(parent)
        self.setupUi(self)
        self._initMemWinProperty()
        self._initTickThread()

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
        self.xspiInstance = 0
        self._initXspiInstanceValue()
        self.xspiNorOpt0 = 0xC0603005
        self.xspiNorOpt1 = 0x0
        self._initXspiNorOptValue()
        self.norFlashModel = None
        self._initNorFlashModelValue()
        self.initFuncUi()

    def _initTickThread( self ):
        self._tickThread = QThread(self)
        self._tickWorker = TickWorker(interval_sec=1)
        self._tickWorker.moveToThread(self._tickThread)
        self._tickThread.started.connect(self._tickWorker.run)
        self._tickWorker.tick.connect(lambda: self.task_doDetectUsbhid())
        self._tickWorker.finished.connect(self._tickThread.quit)
        self._tickWorker.finished.connect(self._tickWorker.deleteLater)
        self._tickThread.finished.connect(self._tickThread.deleteLater)
        self._tickThread.start()

    def _initMemWinProperty( self ):
        font = QFont()
        font.setFamily("Consolas")
        font.setFixedPitch(True)
        font.setPointSize(8)
        self.textEdit_memWin.setFont(font)

    def initFuncUi( self ):
        self.isUartPortSelected = None
        self.isUsbhidPortSelected = None
        self.uartComPort = None
        self.uartBaudrate = None
        self.usbhidVid = None
        self.usbhidPid = None
        self.isUsbhidConnected = False
        self.usbhidToConnect = [None] * 2
        self.blMode = None
        self._initBlModeValue()

    def showAboutMessage( self, myTitle, myContent):
        QMessageBox.about(self, myTitle, myContent )

    def showInfoMessage( self, myTitle, myContent):
        QMessageBox.information(self, myTitle, myContent )

    def _initTargetSetupValue( self ):
        self.comboBox_mcuDevice.clear()
        self.comboBox_mcuDevice.addItems(uidef.kMcuDevice_v1_0)
        self.comboBox_mcuDevice.setCurrentIndex(self.toolCommDict['mcuDevice'])
        self.mcuDevice = self.comboBox_mcuDevice.currentText()

    def setTargetSetupValue( self ):
        self.mcuDevice = self.comboBox_mcuDevice.currentText()
        self.toolCommDict['mcuDevice'] = self.comboBox_mcuDevice.currentIndex()
        uivar.setAdvancedSettings(uidef.kAdvancedSettings_Tool, self.toolCommDict)

    def _initXspiInstanceValue( self ):
        self.xspiInstance = self.toolCommDict['xspiInstance']
        self.comboBox_xspiInstance.setCurrentIndex(self.xspiInstance)

    def setXspiInstanceValue( self ):
        self.xspiInstance = self.comboBox_xspiInstance.currentIndex()
        self.toolCommDict['xspiInstance'] = self.xspiInstance
        uivar.setAdvancedSettings(uidef.kAdvancedSettings_Tool, self.toolCommDict)

    def _initXspiNorOptValue( self ):
        self.xspiNorOpt0 = self.toolCommDict['xspiNorOpt0']
        self.xspiNorOpt1 = self.toolCommDict['xspiNorOpt1']
        self.lineEdit_norCfgOption0.setText(str(hex(self.xspiNorOpt0)))
        self.lineEdit_norCfgOption1.setText(str(hex(self.xspiNorOpt1)))

    def _getXspiNorOptValue( self, optTxt ):
        res = False
        val = 0
        if len(optTxt) > 2 and optTxt[0:2] == '0x':
            try:
                val = int(optTxt[2:len(optTxt)], 16)
                res = True
            except:
                self.popupMsgBox('Nor CFG Option should be like this: 0xc0000001')
        return res, val

    def updateXspiNorOptValue( self ):
        res, val = self._getXspiNorOptValue(self.lineEdit_norCfgOption0.text())
        if res:
            self.xspiNorOpt0 = val
            self.toolCommDict['xspiNorOpt0'] = self.xspiNorOpt0
            res, val = self._getXspiNorOptValue(self.lineEdit_norCfgOption1.text())
            if res:
                self.xspiNorOpt1 = val
                self.toolCommDict['xspiNorOpt1'] = self.xspiNorOpt1

    def _setNorFlashModelCfgValue( self ):
        txt = self.norFlashModel
        self.xspiNorOpt0 = 0x0
        self.xspiNorOpt1 = 0x0
        if txt == uidef.kFlexspiNorDevice_Winbond_W25Q128JV:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Winbond_W25Q128JV
        elif txt == uidef.kFlexspiNorDevice_Winbond_W35T51NW:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Winbond_W35T51NW
        elif txt == uidef.kFlexspiNorDevice_MXIC_MX25L12845G:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_MXIC_MX25L12845G
        elif txt == uidef.kFlexspiNorDevice_MXIC_MX25UM51245G:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_MXIC_MX25UM51245G
        elif txt == uidef.kFlexspiNorDevice_MXIC_MX25UM51345G:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_MXIC_MX25UM51345G
        elif txt == uidef.kFlexspiNorDevice_MXIC_MX25UM51345G_OPI:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_MXIC_MX25UM51345G_OPI
        elif txt == uidef.kFlexspiNorDevice_MXIC_MX25UM51345G_2nd:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_MXIC_MX25UM51345G_2nd
            self.xspiNorOpt1 = uidef.kFlexspiNorOpt1_MXIC_MX25UM51345G_2nd
        elif txt == uidef.kFlexspiNorDevice_GigaDevice_GD25Q64C:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_GigaDevice_GD25Q64C
        elif txt == uidef.kFlexspiNorDevice_GigaDevice_GD25LB256E:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_GigaDevice_GD25LB256E
        elif txt == uidef.kFlexspiNorDevice_GigaDevice_GD25LT256E:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_GigaDevice_GD25LT256E
        elif txt == uidef.kFlexspiNorDevice_GigaDevice_GD25LX256E:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_GigaDevice_GD25LX256E
        elif txt == uidef.kFlexspiNorDevice_ISSI_IS25LP064A:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_ISSI_IS25LP064A
        elif txt == uidef.kFlexspiNorDevice_ISSI_IS25LX256:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_ISSI_IS25LX256
        elif txt == uidef.kFlexspiNorDevice_ISSI_IS26KS512S:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_ISSI_IS26KS512S
        elif txt == uidef.kFlexspiNorDevice_Micron_MT25QL128A:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Micron_MT25QL128A
        elif txt == uidef.kFlexspiNorDevice_Micron_MT35X_RW303:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Micron_MT35X_RW303
        elif txt == uidef.kFlexspiNorDevice_Micron_MT35X_RW304:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Micron_MT35X_RW304
        elif txt == uidef.kFlexspiNorDevice_Adesto_AT25SF128A:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Adesto_AT25SF128A
        elif txt == uidef.kFlexspiNorDevice_Adesto_ATXP032:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Adesto_ATXP032
        elif txt == uidef.kFlexspiNorDevice_Cypress_S25FL064L:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Cypress_S25FL064L
        elif txt == uidef.kFlexspiNorDevice_Cypress_S25FL128S:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Cypress_S25FL128S
        elif txt == uidef.kFlexspiNorDevice_Cypress_S28HS512T:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Cypress_S28HS512T
        elif txt == uidef.kFlexspiNorDevice_Cypress_S26KS512S:
            self.xspiNorOpt0 = uidef.kFlexspiNorOpt0_Cypress_S26KS512S
        else:
            pass
        self.lineEdit_norCfgOption0.setText(str(hex(self.xspiNorOpt0)))
        self.lineEdit_norCfgOption1.setText(str(hex(self.xspiNorOpt1)))

    def _initNorFlashModelValue( self ):
        self.comboBox_norFlashModel.setCurrentIndex(self.toolCommDict['norFlashModel'])
        self.norFlashModel = self.comboBox_norFlashModel.currentText()

    def setNorFlashModelValue( self ):
        self.norFlashModel = self.comboBox_norFlashModel.currentText()
        self.toolCommDict['norFlashModel'] = self.comboBox_norFlashModel.currentIndex()
        self._setNorFlashModelCfgValue()
        uivar.setAdvancedSettings(uidef.kAdvancedSettings_Tool, self.toolCommDict)

    def isInfineonMirrorBitDevice( self ):
        if self.norFlashModel == uidef.kFlexspiNorDevice_ISSI_IS26KS512S or \
           self.norFlashModel == uidef.kFlexspiNorDevice_Cypress_S25FL128S or \
           self.norFlashModel == uidef.kFlexspiNorDevice_Cypress_S28HS512T or \
           self.norFlashModel == uidef.kFlexspiNorDevice_Cypress_S26KS512S:
            return True
        else:
            return False

    def _initBlModeValue( self ):
        self.comboBox_blMode.setCurrentIndex(self.toolCommDict['blMode'])
        self.setBlModeValue()

    def initConnectStage( self ):
        if self.blMode == 0:
            self.connectStage = uidef.kConnectStage_Rom
        elif self.blMode == 1:
            self.connectStage = uidef.kConnectStage_Flashloader
        else:
            pass  

    def setBlModeValue( self ):
        self.blMode = self.comboBox_blMode.currentIndex()
        self.initConnectStage()
        self.toolCommDict['blMode'] = self.blMode
        self._initPortSetupValue()
        uivar.setAdvancedSettings(uidef.kAdvancedSettings_Tool, self.toolCommDict)

    def _initPortSetupValue( self ):
        if self.toolCommDict['isUsbhidPortSelected']:
            self.comboBox_interface.setCurrentIndex(1)
        else:
            self.comboBox_interface.setCurrentIndex(0)
        usbIdList = self.getUsbid()
        self.setPortSetupValue(self.connectStage, usbIdList)

    def task_doDetectUsbhid( self ):
        if self.isUsbhidPortSelected:
            self._retryToDetectUsbhidDevice(False)

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

    def updateConnectStatus( self, color='green' ):
        if color == 'green' or color == 'red':
            self.pushButton_connect.setText('Connnect')
        elif color == 'blue':
            self.pushButton_connect.setText('Reset')
        else:
            return
        self.pushButton_connect.setStyleSheet("color: " + color + ";")

    def updateMemOperateStatus( self, operate, state=0 ):
        if state == 1:
            if operate == uidef.kCommMemOperation_Erase:
                self.pushButton_erase.setStyleSheet("background-color: yellow;")
                self.pushButton_erase.setEnabled(False)
            elif operate == uidef.kCommMemOperation_EraseChip:
                self.pushButton_eraseChip.setStyleSheet("background-color: yellow;")
                self.pushButton_eraseChip.setEnabled(False)
            elif operate == uidef.kCommMemOperation_Read:
                self.pushButton_read.setStyleSheet("background-color: yellow;")
                self.pushButton_read.setEnabled(False)
            elif operate == uidef.kCommMemOperation_Write:
                self.pushButton_write.setStyleSheet("background-color: yellow;")
                self.pushButton_write.setEnabled(False)
            else:
                pass
        elif state == 0:
            self.pushButton_erase.setStyleSheet("background-color: white;")
            self.pushButton_erase.setEnabled(True)
            self.pushButton_eraseChip.setStyleSheet("background-color: white;")
            self.pushButton_eraseChip.setEnabled(True)
            self.pushButton_read.setStyleSheet("background-color: white;")
            self.pushButton_read.setEnabled(True)
            self.pushButton_write.setStyleSheet("background-color: white;")
            self.pushButton_write.setEnabled(True)
        else:
            pass

    def popupMsgBox( self, msgStr, myTitle="Error"):
        QMessageBox.information(self, myTitle, msgStr )

    def task_startGauge( self ):
        if getattr(self, "progress_timer", None):
            self.progress_timer.stop()
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(int(self.gaugeIntervalSec * 1000))

        def _tick_progress_to_99():
            gaugePercentage = self.curGauge * 1.0 / self.maxGauge
            if gaugePercentage <= 0.9:
                gaugeIntervalSec = int(gaugePercentage  / 0.1) * 0.5 + 0.5
                delayCnt = int(gaugeIntervalSec / self.gaugeIntervalSec)
                if self.timerDelayCnt > delayCnt:
                    self.timerDelayCnt = 0
                    val = self.progressBar_action.value()
                    if val < self.maxGauge:
                        self.progressBar_action.setValue(val + 1)
                        self.curGauge = val + 1
                else:
                    self.timerDelayCnt += 1

        self.progress_timer.timeout.connect(_tick_progress_to_99)
        self.progress_timer.start()

    def initGauge( self ):
        self.timerDelayCnt = 1
        self.curGauge = 0
        self.gaugeIntervalSec = 0.5
        self.maxGauge = self.progressBar_action.maximum()
        self.progressBar_action.setValue(self.curGauge)

    def deinitGauge( self ):
        self.curGauge = self.maxGauge
        self.timerDelayCnt = 1
        self.gaugeIntervalSec = 1
        if getattr(self, "progress_timer", None):
            self.progress_timer.stop()
        self.progressBar_action.setValue(self.maxGauge)

    def convertLongIntHexText( self, hexText ):
        lastStr = hexText[len(hexText) - 1]
        if lastStr == 'l' or lastStr == 'L':
            return hexText[0:len(hexText) - 1]
        else:
            return hexText

    def printDeviceStatus( self, statusStr ):
        self.textEdit_commStatus.append(statusStr)

    def clearDeviceStatus( self ):
        self.textEdit_commStatus.clear()

    def getFormattedFuseValue( self, fuseValue, direction='LSB'):
        formattedVal32 = ''
        for i in range(8):
            loc = 0
            if direction =='LSB':
                loc = 32 - (i + 1) * 4
            elif direction =='MSB':
                loc = i * 4
            else:
                pass
            halfbyteStr = str(hex((fuseValue & (0xF << loc))>> loc))
            formattedVal32 += halfbyteStr[2]
        return formattedVal32

    def getFormattedHexValue( self, val32 ):
        return ('0x' + self.getFormattedFuseValue(val32))

    def getFormattedUpperHexValue( self, val32 ):
        return ('0x' + self.getFormattedFuseValue(val32).upper())

    def getVal32FromHexText( self, hexText ):
        status = False
        val32 = None
        if len(hexText) > 2 and hexText[0:2] == '0x':
            try:
                val32 = int(hexText[2:len(hexText)], 16)
                status = True
            except:
                pass
        if not status:
            self.popupMsgBox('Range property should be like this: 0x2000')
        return status, val32

    def getComMemStartAddress( self ):
        return self.getVal32FromHexText(self.lineEdit_rangeStart.text())

    def getComMemByteLength( self ):
        return self.getVal32FromHexText(self.lineEdit_rangeLength.text())

    def browseFile( self ):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", "All (*);;BIN (*.bin)"
        )
        if path:
            self.lineEdit_browseFile.setText(path)
            self.memBinFile = path

    def getComMemBinFile( self ):
        return self.memBinFile

    def getOtaFileStartAddress( self, fileType = 'stage0Bl' ):
        status = False
        val32 = None
        self.otaMemStart = None
        if fileType == uidef.kOtaFileType_S0BL:
            status, val32 = self.getVal32FromHexText(self.lineEdit_fileStartS0BL.text())
        elif fileType == uidef.kOtaFileType_S1BL:
            status, val32 = self.getVal32FromHexText(self.lineEdit_fileStartS1BL.text())
        elif fileType == uidef.kOtaFileType_APP0:
            status, val32 = self.getVal32FromHexText(self.lineEdit_fileStartAPP0.text())
        elif fileType == uidef.kOtaFileType_APP1:
            status, val32 = self.getVal32FromHexText(self.lineEdit_fileStartAPP1.text())
        else:
            pass
        if status:
            self.otaMemStart = val32
        
    def browseOtaFile( self, fileType = 'stage0Bl' ):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", "All (*);;BIN (*.bin)"
        )
        if path:
            if fileType == uidef.kOtaFileType_S0BL:
                self.lineEdit_stage0BlFile.setText(path)
                self.stage0BlFile = path
            elif fileType == uidef.kOtaFileType_S1BL:
                self.lineEdit_stage1BlFile.setText(path)
                self.stage1BlFile = path
            elif fileType == uidef.kOtaFileType_APP0:
                self.lineEdit_appSlot0File.setText(path)
                self.appSlot0File = path
            elif fileType == uidef.kOtaFileType_APP1:
                self.lineEdit_appSlot1File.setText(path)
                self.appSlot1File = path
            else:
                pass

    def updateOtaOperateStatus( self, operate, state=0 ):
        if state == 1:
            if operate == uidef.kOtaFileType_S0BL:
                self.pushButton_downloadS0BL.setStyleSheet("background-color: yellow;")
                self.pushButton_downloadS0BL.setEnabled(False)
            elif operate == uidef.kOtaFileType_S1BL:
                self.pushButton_downloadS1BL.setStyleSheet("background-color: yellow;")
                self.pushButton_downloadS1BL.setEnabled(False)
            elif operate == uidef.kOtaFileType_APP0:
                self.pushButton_downloadAPP0.setStyleSheet("background-color: yellow;")
                self.pushButton_downloadAPP0.setEnabled(False)
            elif operate == uidef.kOtaFileType_APP1:
                self.pushButton_downloadAPP1.setStyleSheet("background-color: yellow;")
                self.pushButton_downloadAPP1.setEnabled(False)
            else:
                pass
        elif state == 0:
            self.pushButton_downloadS0BL.setStyleSheet("background-color: white;")
            self.pushButton_downloadS0BL.setEnabled(True)
            self.pushButton_downloadS1BL.setStyleSheet("background-color: white;")
            self.pushButton_downloadS1BL.setEnabled(True)
            self.pushButton_downloadAPP0.setStyleSheet("background-color: white;")
            self.pushButton_downloadAPP0.setEnabled(True)
            self.pushButton_downloadAPP1.setStyleSheet("background-color: white;")
            self.pushButton_downloadAPP1.setEnabled(True)
        else:
            pass

    def printMem( self , memStr ):
        self.textEdit_memWin.append(memStr)

    def clearMem( self ):
        self.textEdit_memWin.clear()

