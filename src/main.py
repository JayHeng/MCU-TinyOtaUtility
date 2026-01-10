#! /usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import os
import time
import threading
from PyQt5.Qt import *
from ui import uidef
from ui import uilang
from ui import uivar
from mem import memcore

g_main_win = None
g_task_detectUsbhid = None
g_task_increaseGauge = None
g_task_accessMem = None

kRetryPingTimes = 2

kBootloaderType_Rom         = 0
kBootloaderType_Flashloader = 1

class tinyOtaMain(memcore.tinyOtaMem):

    def __init__(self, parent=None):
        super(tinyOtaMain, self).__init__(parent)
        self._register_callbacks()
        self._initMain()

    def _initMain( self ):
        self.isAccessMemTaskPending = False
        self.accessMemType = ''

    def _startGaugeTimer( self ):
        self.initGauge()

    def _stopGaugeTimer( self ):
        self.deinitGauge()

    def _register_callbacks(self):
        self.menuHelpAction_homePage.triggered.connect(self.callbackShowHomePage)
        self.menuHelpAction_aboutAuthor.triggered.connect(self.callbackShowAboutAuthor)
        self.menuHelpAction_revisionHistory.triggered.connect(self.callbackShowRevisionHistory)
        self.comboBox_mcuDevice.currentIndexChanged.connect(self.callbackSetMcuDevice)
        self.comboBox_norFlashModel.currentIndexChanged.connect(self.callbackSetNorFlashModel)
        self.comboBox_xspiInstance.currentIndexChanged.connect(self.callbackSetXspiInstance)
        self.comboBox_interface.currentIndexChanged.connect(self.callbackSetInterface)
        self.comboBox_blMode.currentIndexChanged.connect(self.callbackSetBlMode)
        self.pushButton_connect.clicked.connect(self.callbackConnectToDevice)
        self.pushButton_read.clicked.connect(self.callbackReadMem)
        self.pushButton_write.clicked.connect(self.callbackWriteMem)
        self.pushButton_erase.clicked.connect(self.callbackEraseMem)

    def _setupMcuTargets( self ):
        self.setTargetSetupValue()
        self.initFuncUi()
        self.initFuncRun()
        self._setUartUsbPort()

    def callbackSetMcuDevice( self ):
        self._setupMcuTargets()

    def callbackSetNorFlashModel( self ):
        self.setNorFlashModelValue()

    def callbackSetXspiInstance( self ):
        self.setXspiInstanceValue()

    def _setUartUsbPort( self ):
        usbIdList = self.getUsbid()
        retryToDetectUsb = False
        showError = True
        self.setPortSetupValue(self.connectStage, usbIdList, retryToDetectUsb, showError)

    def callbackSetInterface( self ):
        self._setUartUsbPort()

    def callbackSetBlMode( self ):
        self.setBlModeValue()

    def _retryToPingBootloader( self, bootType ):
        pingStatus = False
        pingCnt = kRetryPingTimes
        while (not pingStatus) and pingCnt > 0:
            if bootType == kBootloaderType_Rom:
                pingStatus = self.pingRom()
            elif bootType == kBootloaderType_Flashloader:
                # This is mainly for RT1170 flashloader, but it is also ok for other RT devices
                if (not self.isUsbhidPortSelected):
                    time.sleep(3)
                pingStatus = self.pingFlashloader()
            else:
                pass
            if pingStatus:
                break
            pingCnt = pingCnt - 1
            if self.isUsbhidPortSelected:
                time.sleep(2)
        return pingStatus

    def _connectFailureHandler( self ):
        self.initConnectStage()
        self.updateConnectStatus('red')
        usbIdList = self.getUsbid()
        self.setPortSetupValue(self.connectStage, usbIdList, False, False)

    def callbackConnectToDevice( self ):
        while True:
            if not self.updatePortSetupValue(False, True):
                if self.connectStage == uidef.kConnectStage_Rom:
                    self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_doubleCheckBmod'][0])
                self._connectFailureHandler()
                return
            if self.connectStage == uidef.kConnectStage_Rom:
                self.connectToDevice(self.connectStage)
                if self._retryToPingBootloader(kBootloaderType_Rom):
                    self.getMcuDeviceInfoViaRom()
                    self.getMcuDeviceHabStatus()
                    if self.jumpToFlashloader():
                        self.connectStage = uidef.kConnectStage_Flashloader
                        usbIdList = self.getUsbid()
                        self.setPortSetupValue(self.connectStage, usbIdList, True, True)
                    else:
                        self.updateConnectStatus('red')
                        self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_failToJumpToFl'][0])
                        return
                else:
                    self.updateConnectStatus('red')
                    self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_doubleCheckBmod'][0])
                    return
            elif self.connectStage == uidef.kConnectStage_Flashloader:
                self.connectToDevice(self.connectStage)
                if self._retryToPingBootloader(kBootloaderType_Flashloader):
                    self.getMcuDeviceInfoViaFlashloader()
                    self.connectStage = uidef.kConnectStage_ExternalMemory
                else:
                    self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_failToPingFl'][0])
                    self._connectFailureHandler()
                    return
            elif self.connectStage == uidef.kConnectStage_ExternalMemory:
                if self.configureBootDevice():
                    self.getBootDeviceInfoViaFlashloader()
                    self.connectStage = uidef.kConnectStage_Reset
                    self.updateConnectStatus('blue')
                else:
                    self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_failToCfgBootDevice'][0])
                    self._connectFailureHandler()
                return
            elif self.connectStage == uidef.kConnectStage_Reset:
                self.resetMcuDevice()
                self.initConnectStage()
                self.updateConnectStatus('green')
                usbIdList = self.getUsbid()
                self.setPortSetupValue(self.connectStage, usbIdList, True, True)
                self.connectToDevice(self.connectStage)
                return
            else:
                pass

    def task_doAccessMem( self ):
        while True:
            if self.isAccessMemTaskPending:
                if self.accessMemType == 'ReadMem':
                    self.readXspiFlashMemory()
                elif self.accessMemType == 'EraseMem':
                    self.eraseXspiFlashMemory()
                elif self.accessMemType == 'WriteMem':
                    self.writeXspiFlashMemory()
                else:
                    pass
                self.isAccessMemTaskPending = False
                self._stopGaugeTimer()
            time.sleep(1)

    def callbackReadMem( self, event ):
        if self.connectStage == uidef.kConnectStage_Reset:
            #self._startGaugeTimer()
            #self.isAccessMemTaskPending = True
            #self.accessMemType = 'ReadMem'
            self.readXspiFlashMemory()
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotEnterFl'][0])

    def callbackEraseMem( self, event ):
        if self.connectStage == uidef.kConnectStage_Reset:
            #self._startGaugeTimer()
            #self.isAccessMemTaskPending = True
            #self.accessMemType = 'EraseMem'
            self.eraseXspiFlashMemory()
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])

    def callbackWriteMem( self, event ):
        if self.connectStage == uidef.kConnectStage_Reset:
            #self._startGaugeTimer()
            #self.isAccessMemTaskPending = True
            #self.accessMemType = 'WriteMem'
            self.writeXspiFlashMemory()
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotEnterFl'][0])

    def _deinitToolToExit( self ):
        self.updateXspiNorOptValue()
        uivar.setAdvancedSettings(uidef.kAdvancedSettings_Tool, self.toolCommDict)
        uivar.deinitVar()

    def closeEvent(self, event):
        self._deinitToolToExit()
        event.accept()

    def callbackShowHomePage(self):
        self.showAboutMessage(uilang.kMsgLanguageContentDict['homePage_title'][0], uilang.kMsgLanguageContentDict['homePage_info'][0] )

    def callbackShowAboutAuthor(self):
        msgText = ((uilang.kMsgLanguageContentDict['aboutAuthor_author'][0]) +
                   (uilang.kMsgLanguageContentDict['aboutAuthor_email1'][0]) +
                   (uilang.kMsgLanguageContentDict['aboutAuthor_email2'][0]) +
                   (uilang.kMsgLanguageContentDict['aboutAuthor_blog'][0]))
        self.showAboutMessage(uilang.kMsgLanguageContentDict['aboutAuthor_title'][0], msgText )

    def callbackShowRevisionHistory(self):
        self.showAboutMessage(uilang.kMsgLanguageContentDict['revisionHistory_title'][0], uilang.kMsgLanguageContentDict['revisionHistory_v1_0_0'][0] )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    g_main_win = tinyOtaMain(None)
    g_main_win.setWindowTitle(u"MCU Tiny OTA Utility v1.0")
    g_main_win.show()

    g_task_detectUsbhid = threading.Thread(target=g_main_win.task_doDetectUsbhid)
    g_task_detectUsbhid.setDaemon(True)
    g_task_detectUsbhid.start()
    #g_task_increaseGauge = threading.Thread(target=g_main_win.task_doIncreaseGauge)
    #g_task_increaseGauge.setDaemon(True)
    #g_task_increaseGauge.start()
    #g_task_accessMem = threading.Thread(target=g_main_win.task_doAccessMem)
    #g_task_accessMem.setDaemon(True)
    #g_task_accessMem.start()

    sys.exit(app.exec_())

