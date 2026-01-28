#! /usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import os
import time
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

class otaWorkerBase(QObject):
    finished = pyqtSignal(object)
    def __init__(self, owner):
        super().__init__(None)
        self._owner = owner

class otaWorkerS0BL(otaWorkerBase):
    @pyqtSlot()
    def run(self):
        try:
            self._owner.downloadOtaFile(uidef.kOtaFileType_S0BL)
            self.finished.emit(None)
        except Exception as e:
            pass
class otaWorkerS1BL(otaWorkerBase):
    @pyqtSlot()
    def run(self):
        try:
            self._owner.downloadOtaFile(uidef.kOtaFileType_S1BL)
            self.finished.emit(None)
        except Exception as e:
            pass
class otaWorkerAPP0(otaWorkerBase):
    @pyqtSlot()
    def run(self):
        try:
            self._owner.downloadOtaFile(uidef.kOtaFileType_APP0)
            self.finished.emit(None)
        except Exception as e:
            pass
class otaWorkerAPP1(otaWorkerBase):
    @pyqtSlot()
    def run(self):
        try:
            self._owner.downloadOtaFile(uidef.kOtaFileType_APP1)
            self.finished.emit(None)
        except Exception as e:
            pass

class memOperateWorker(QObject):
    started  = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, owner, task_file_type):
        super().__init__(None)
        self._owner = owner
        self._task  = task_file_type

    def run(self):
        self.started.emit()
        try:
            if self._task == uidef.kCommMemOperation_Erase:
                self._owner.eraseXspiFlashMemory()
            elif self._task == uidef.kCommMemOperation_EraseChip:
                self._owner.massEraseXspiFlashMemory()
            elif self._task == uidef.kCommMemOperation_Write:
                self._owner.writeXspiFlashMemory()
            else:
                self._owner.downloadOtaFile(self._task)
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
        self.otaOperateThread = None
        self.otaOperateWorker = None

        self._otaThreads = set()

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
        self.pushButton_makeS1BL.clicked.connect(self.callbackMakeS1BL)
        self.pushButton_makeAPP0.clicked.connect(self.callbackMakeAPP0)
        self.pushButton_makeAPP1.clicked.connect(self.callbackMakeAPP1)
        self.pushButton_downloadS0BL.clicked.connect(self.callbackDownloadS0BL)
        self.pushButton_downloadS1BL.clicked.connect(self.callbackDownloadS1BL)
        self.pushButton_downloadAPP0.clicked.connect(self.callbackDownloadAPP0)
        self.pushButton_downloadAPP1.clicked.connect(self.callbackDownloadAPP1)
        self.pushButton_allInOne.clicked.connect(self.callbackAllInOne)

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
            self.updateMemOperateStatus(self.accessMemType, 0)
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])

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
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])

    def callbackBrowseS0BL( self ):
        self.browseOtaFile(uidef.kOtaFileType_S0BL)
        self.updateOtaOperateStatus(uidef.kOtaFileType_S0BL, 0)
    def callbackBrowseS1BL( self ):
        self.browseOtaFile(uidef.kOtaFileType_S1BL)
        self.updateOtaMakeStatus(uidef.kOtaFileType_S1BL, 0)
        self.updateOtaOperateStatus(uidef.kOtaFileType_S1BL, 0)
    def callbackBrowseAPP0( self ):
        self.browseOtaFile(uidef.kOtaFileType_APP0)
        self.updateOtaMakeStatus(uidef.kOtaFileType_APP0, 0)
        self.updateOtaOperateStatus(uidef.kOtaFileType_APP0, 0)
    def callbackBrowseAPP1( self ):
        self.browseOtaFile(uidef.kOtaFileType_APP1)
        self.updateOtaMakeStatus(uidef.kOtaFileType_APP1, 0)
        self.updateOtaOperateStatus(uidef.kOtaFileType_APP1, 0)

    def _makeOtaFile( self, fileType ):
        if self.makeOtaFile(fileType):
            self.updateOtaMakeStatus(fileType, 1)
        else:
            self.updateOtaMakeStatus(fileType, 0)

    def callbackMakeS1BL( self ):
        self.showImagePiture('boot')
        self._makeOtaFile(uidef.kOtaFileType_S1BL)
    def callbackMakeAPP0( self ):
        self.showImagePiture('app')
        self._makeOtaFile(uidef.kOtaFileType_APP0)
    def callbackMakeAPP1( self ):
        self.showImagePiture('app')
        self._makeOtaFile(uidef.kOtaFileType_APP1)

    def _startDownloadOtaTask( self, fileType ):
        self.initGauge()
        self.task_startGauge()
        self.otaOperateThread = QThread(self)
        self.otaOperateWorker = memOperateWorker(self, fileType)
        self.otaOperateWorker.moveToThread(self.otaOperateThread)
        self.otaOperateThread.started.connect(self.otaOperateWorker.run)
        self.otaOperateWorker.finished.connect(lambda: (
            self.updateOtaOperateStatus(fileType, 2),
            self.deinitGauge(),
            self.otaOperateThread.quit()
        ))
        self.otaOperateWorker.finished.connect(self.otaOperateWorker.deleteLater)
        self.otaOperateThread.finished.connect(self.otaOperateThread.deleteLater)
        self.otaOperateThread.start()

    def _downloadOtaFile( self, fileType ):
        self.getOtaFileStartAddress(fileType)
        self.updateOtaOperateStatus(fileType, 1)
        self._startDownloadOtaTask(fileType)

    def callbackDownloadS0BL( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self._downloadOtaFile(uidef.kOtaFileType_S0BL)
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])
    def callbackDownloadS1BL( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self._downloadOtaFile(uidef.kOtaFileType_S1BL)
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])
    def callbackDownloadAPP0( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self._downloadOtaFile(uidef.kOtaFileType_APP0)
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])
    def callbackDownloadAPP1( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self._downloadOtaFile(uidef.kOtaFileType_APP1)
        else:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_hasnotCfgBootDevice'][0])

    def _start_ota_worker(self, worker_obj, on_finished=None):
        thread = QThread(self)
        worker_obj.moveToThread(thread)
        def cleanup(result=None):
            thread.quit()
            thread.wait()
            worker_obj.deleteLater()
            thread.deleteLater()
            if thread in self._otaThreads:
                self._otaThreads.remove(thread)
            if on_finished:
                on_finished(result)
        thread.started.connect(worker_obj.run)
        worker_obj.finished.connect(cleanup)
        self._otaThreads.add(thread)
        thread.start()
        return worker_obj

    def callbackAllInOne( self ):
        self.initGauge()
        self.task_startGauge()
        worker_S1BL = otaWorkerS1BL(self)
        def after_S1BL(res_S1BL):
            self.updateOtaOperateStatus(uidef.kOtaFileType_S1BL, 2)
            worker_APP0 = otaWorkerAPP0(self)
            def after_APP0(res_APP0):
                self.updateOtaOperateStatus(uidef.kOtaFileType_APP0, 2)
                worker_APP1 = otaWorkerAPP1(self)
                def after_APP1(res_APP1):
                    self.updateOtaOperateStatus(uidef.kOtaFileType_APP1, 2)
                    self.showImagePiture('all_single_core')
                    self.deinitGauge()
                if self.makeOtaFile(uidef.kOtaFileType_APP1):
                    self.updateOtaMakeStatus(uidef.kOtaFileType_APP1, 1)
                else:
                    self.updateOtaMakeStatus(uidef.kOtaFileType_APP1, 0)
                    return
                self.getOtaFileStartAddress(uidef.kOtaFileType_APP1)
                self.updateOtaOperateStatus(uidef.kOtaFileType_APP1, 1) 
                self._start_ota_worker(worker_APP1, on_finished=after_APP1)
            if self.makeOtaFile(uidef.kOtaFileType_APP0):
                self.updateOtaMakeStatus(uidef.kOtaFileType_APP0, 1)
            else:
                self.updateOtaMakeStatus(uidef.kOtaFileType_APP0, 0)
                return
            self.getOtaFileStartAddress(uidef.kOtaFileType_APP0)
            self.updateOtaOperateStatus(uidef.kOtaFileType_APP0, 1) 
            self._start_ota_worker(worker_APP0, on_finished=after_APP0)
        if self.makeOtaFile(uidef.kOtaFileType_S1BL):
            self.updateOtaMakeStatus(uidef.kOtaFileType_S1BL, 1)
        else:
            self.updateOtaMakeStatus(uidef.kOtaFileType_S1BL, 0)
            return
        self.getOtaFileStartAddress(uidef.kOtaFileType_S1BL)
        self.updateOtaOperateStatus(uidef.kOtaFileType_S1BL, 1)
        self._start_ota_worker(worker_S1BL, on_finished=after_S1BL)

    def _deinitToolToExit( self ):
        self.updateXspiNorOptValue()
        uivar.setAdvancedSettings(uidef.kAdvancedSettings_Tool, self.toolCommDict)
        uivar.deinitVar()

    def _stopThreads(self):
        try:
            if self.memOperateWorker:
                self.memOperateWorker.stop()
            if self.memOperateThread:
                self.memOperateThread.quit()
                if not self.memOperateThread.wait(2000):
                    self.memOperateThread.terminate()
                    self.memOperateThread.wait()
            self.memOperateWorker = None
            self.memOperateThread = None
        except:
            pass

        try:
            if self.otaOperateWorker:
                self.otaOperateWorker.stop()
            if self.otaOperateThread:
                self.otaOperateThread.quit()
                if not self.otaOperateThread.wait(2000):
                    self.otaOperateThread.terminate()
                    self.otaOperateThread.wait()
            self.otaOperateWorker = None
            self.otaOperateThread = None
        except:
            pass

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
        msgText = ((uilang.kMsgLanguageContentDict['revisionHistory_v1_0_0'][0]) +
                   (uilang.kMsgLanguageContentDict['revisionHistory_v1_1_0'][0]))
        self.showAboutMessage(uilang.kMsgLanguageContentDict['revisionHistory_title'][0], msgText)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    g_main_win = tinyOtaMain(None)
    g_main_win.setWindowTitle(u"MCU Tiny OTA Utility v1.1")
    g_main_win.show()

    sys.exit(app.exec_())

