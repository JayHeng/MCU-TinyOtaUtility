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

import warnings
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*sipPyTypeDict\(\).*"
)


g_main_win = None

kRetryPingTimes = 2

kBootloaderType_Rom         = 0
kBootloaderType_Flashloader = 1

class memOperateWorker(QObject):
    started  = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, owner, task_type):
        super().__init__(None)
        self._owner = owner
        self._task  = task_type
        self._stop  = False

    def stop(self):
        self._stop = True

    def run(self):
        self.started.emit()
        try:
            if self._task == uidef.kCommMemOperation_Erase:
                self._owner.eraseXspiFlashMemory()
            elif self._task == uidef.kCommMemOperation_EraseChip:
                self._owner.massEraseXspiFlashMemory()
            elif self._task == uidef.kCommMemOperation_Write:
                self._owner.writeXspiFlashMemory()
            self.finished.emit()
        except Exception as e:
            pass

class tinyOtaMain(memcore.tinyOtaMem):

    def __init__(self, parent=None):
        super(tinyOtaMain, self).__init__(parent)
        self._register_callbacks()
        self._initMain()

    def _initMain( self ):
        self.accessMemType = ''
        self.memOperateThread = None
        self.memOperateWorker = None

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
        self.pushButton_eraseChip.clicked.connect(self.callbackEraseMemChip)
        self.pushButton_browseFile.clicked.connect(self.callbackBrowseFile)
        self.pushButton_stage0BlFile.clicked.connect(self.callbackBrowseS0BL)
        self.pushButton_stage1BlFile.clicked.connect(self.callbackBrowseS1BL)
        self.pushButton_appSlot0File.clicked.connect(self.callbackBrowseAPP0)
        self.pushButton_appSlot1File.clicked.connect(self.callbackBrowseAPP1)
        self.pushButton_downloadS0BL.clicked.connect(self.callbackDownloadS0BL)
        self.pushButton_downloadS1BL.clicked.connect(self.callbackDownloadS1BL)
        self.pushButton_downloadAPP0.clicked.connect(self.callbackDownloadAPP0)
        self.pushButton_downloadAPP1.clicked.connect(self.callbackDownloadAPP1)

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

    def _startMemOperateTask( self, taskType ):
        self.initGauge()
        self.task_startGauge()
        self.memOperateThread = QThread(self)
        self.memOperateWorker = memOperateWorker(self, taskType)
        self.memOperateWorker.moveToThread(self.memOperateThread)
        self.memOperateThread.started.connect(self.memOperateWorker.run)
        self.memOperateWorker.finished.connect(lambda: (
            self.updateMemOperateStatus(taskType, 0),
            self.deinitGauge(),
            self.memOperateThread.quit()
        ))
        self.memOperateWorker.finished.connect(self.memOperateWorker.deleteLater)
        self.memOperateThread.finished.connect(self.memOperateThread.deleteLater)
        self.memOperateThread.start()

    def callbackReadMem( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self.accessMemType = uidef.kCommMemOperation_Read
            self.getUserComMemParameters(False)
            self.updateMemOperateStatus(self.accessMemType, 1)
            self.readXspiFlashMemory()
            self.updateMemOperateStatus(self.accessMemType, 0),
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotEnterFl'][0])

    def callbackEraseMem( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self.accessMemType = uidef.kCommMemOperation_Erase
            self.getUserComMemParameters(False)
            self.updateMemOperateStatus(self.accessMemType, 1)
            self._startMemOperateTask(self.accessMemType)
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])

    def callbackEraseMemChip( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self.accessMemType = uidef.kCommMemOperation_EraseChip
            self.updateMemOperateStatus(self.accessMemType, 1)
            self._startMemOperateTask(self.accessMemType)
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])

    def callbackBrowseFile( self ):
        self.browseFile()

    def callbackWriteMem( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self.accessMemType = uidef.kCommMemOperation_Write
            self.getUserComMemParameters(True)
            self.updateMemOperateStatus(self.accessMemType, 1)
            self._startMemOperateTask(self.accessMemType)
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotEnterFl'][0])

    def callbackBrowseS0BL( self ):
        self.browseOtaFile(uidef.kOtaFileType_S0BL)
    def callbackBrowseS1BL( self ):
        self.browseOtaFile(uidef.kOtaFileType_S1BL)
    def callbackBrowseAPP0( self ):
        self.browseOtaFile(uidef.kOtaFileType_APP0)
    def callbackBrowseAPP1( self ):
        self.browseOtaFile(uidef.kOtaFileType_APP1)

    def _downloadOtaFile( self, fileType ):
        self.getOtaFileStartAddress(fileType)
        self.updateOtaOperateStatus(fileType, 1)
        self.downloadOtaFile(fileType)
        self.updateOtaOperateStatus(fileType, 0)

    def callbackDownloadS0BL( self ):
        self._downloadOtaFile(uidef.kOtaFileType_S0BL)
    def callbackDownloadS1BL( self ):
        self._downloadOtaFile(uidef.kOtaFileType_S1BL)
    def callbackDownloadAPP0( self ):
        self._downloadOtaFile(uidef.kOtaFileType_APP0)
    def callbackDownloadAPP1( self ):
        self._downloadOtaFile(uidef.kOtaFileType_APP1)

    def _deinitToolToExit( self ):
        self.updateXspiNorOptValue()
        uivar.setAdvancedSettings(uidef.kAdvancedSettings_Tool, self.toolCommDict)
        uivar.deinitVar()

    def _stopThreads(self):
        if self.memOperateWorker:
            self.memOperateWorker.stop()
        if self.memOperateThread:
            self.memOperateThread.quit()
            if not self.memOperateThread.wait(2000):
                self.memOperateThread.terminate()
                self.memOperateThread.wait()
        self.memOperateWorker = None
        self.memOperateThread = None
        if self._tickWorker:
            self._tickWorker.stop()
        if self._tickThread:
            self._tickThread.quit()
            if not self._tickThread.wait(2000):
                self._tickThread.terminate()
                self._tickThread.wait()
        self._tickWorker = None
        self._tickThread = None

    def closeEvent(self, event):
        self._stopThreads()
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

    sys.exit(app.exec_())

