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
from run import runcore

g_main_win = None
g_task_detectUsbhid = None

class tinyOtaMain(runcore.tinyOtaRun):

    def __init__(self, parent=None):
        super(tinyOtaMain, self).__init__(parent)
        self._register_callbacks()
        self._initMain()

    def _initMain( self ):
        self.connectStage = uidef.kConnectStage_Rom

    def _register_callbacks(self):
        self.menuHelpAction_homePage.triggered.connect(self.callbackShowHomePage)
        self.menuHelpAction_aboutAuthor.triggered.connect(self.callbackShowAboutAuthor)
        self.menuHelpAction_revisionHistory.triggered.connect(self.callbackShowRevisionHistory)
        self.comboBox_mcuDevice.currentIndexChanged.connect(self.callbackSetMcuDevice)
        self.comboBox_interface.currentIndexChanged.connect(self.callbackSetInterface)
        self.pushButton_connect.clicked.connect(self.callbackConnectToDevice)

    def _setupMcuTargets( self ):
        self.setTargetSetupValue()
        self.initFuncUi()
        self.initFuncRun()
        self._setUartUsbPort()

    def callbackSetMcuDevice( self ):
        self._setupMcuTargets()

    def _setUartUsbPort( self ):
        usbIdList = self.getUsbid()
        retryToDetectUsb = False
        showError = True
        self.setPortSetupValue(self.connectStage, usbIdList, retryToDetectUsb, showError)

    def callbackSetInterface( self ):
        self._setUartUsbPort()

    def callbackConnectToDevice( self ):
        pass

    def _deinitToolToExit( self ):
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

    sys.exit(app.exec_())

