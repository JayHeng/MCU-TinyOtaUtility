#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2022 NXP
# All rights reserved.
# 
# SPDX-License-Identifier: BSD-3-Clause

import sys
import os
import array
from . import rundef
sys.path.append(os.path.abspath(".."))
import boot
from ui import uicore
from ui import uidef
from ui import uilang
from boot import bltest
from boot import target
from utils import misc

def createTarget(device, exeBinRoot):
    cpu = "MIMXRT1176"
    if device == uidef.kMcuDevice_iMXRT117x:
        cpu = "MIMXRT1176"
    elif device == uidef.kMcuDevice_iMXRT118x:
        cpu = "MIMXRT1189"
    else:
        pass
    targetBaseDir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'targets', cpu)

    # Check for existing target directory.
    if not os.path.isdir(targetBaseDir):
        targetBaseDir = os.path.join(os.path.dirname(exeBinRoot), 'src', 'targets', cpu)
        if not os.path.isdir(targetBaseDir):
            raise ValueError("Missing target directory at path %s" % targetBaseDir)

    targetConfigFile = os.path.join(targetBaseDir, 'bltargetconfig.py')

    # Check for config file existence.
    if not os.path.isfile(targetConfigFile):
        raise RuntimeError("Missing target config file at path %s" % targetConfigFile)

    # Build locals dict by copying our locals and adjusting file path and name.
    targetConfig = locals().copy()
    targetConfig['__file__'] = targetConfigFile
    targetConfig['__name__'] = 'bltargetconfig'

    # Execute the target config script.
    misc.execfile(targetConfigFile, globals(), targetConfig)

    # Create the target object.
    tgt = target.Target(**targetConfig)

    return tgt, targetBaseDir

class tinyOtaRun(uicore.tinyOtaUi):

    def __init__(self, parent=None):
        super(tinyOtaRun, self).__init__(parent)
        self.initFuncRun()

    def initFuncRun( self ):
        self.blhost = None
        self.sdphost = None
        self.tgt = None
        self.cpuDir = None
        self.sdphostVectorsDir = os.path.join(self.exeTopRoot, 'tools', 'sdphost', 'win', 'vectors')
        self.blhostVectorsDir = os.path.join(self.exeTopRoot, 'tools', 'blhost2_6', 'win', 'vectors')
        self.createMcuTarget()

    def createMcuTarget( self ):
        self.tgt, self.cpuDir = createTarget(self.mcuDevice, self.exeBinRoot)

    def connectToDevice( self ):
        # Create the target object.
        self.createMcuTarget()
        xhost = None
        if self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT10yy:
            xhost = 'sdp_'
        elif (self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT11yy) or \
             (self.tgt.mcuSeries == uidef.kMcuSeries_iMXRTxxx):
            xhost = ''
        else:
            pass

        xPeripheral = xhost + 'uart'
        uartComPort = self.uartComPort
        uartBaudrate = int(self.uartBaudrate)
        usbVid = ''
        usbPid = ''

        if self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT10yy:
            self.sdphost = bltest.createBootloader(self.tgt,
                                                   self.sdphostVectorsDir,
                                                   xPeripheral,
                                                   uartBaudrate, uartComPort,
                                                   usbVid, usbPid)
        elif (self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT11yy) or \
             (self.tgt.mcuSeries == uidef.kMcuSeries_iMXRTxxx):
            self.blhost = bltest.createBootloader(self.tgt,
                                                  self.blhostVectorsDir,
                                                  xPeripheral,
                                                  uartBaudrate, uartComPort,
                                                  usbVid, usbPid,
                                                  True)
        else:
            pass

    def pingRom( self ):
        if self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT10yy:
            status, results, cmdStr = self.sdphost.errorStatus()
            return (status == boot.status.kSDP_Status_HabEnabled or status == boot.status.kSDP_Status_HabDisabled)
        elif (self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT11yy) or \
             (self.tgt.mcuSeries == uidef.kMcuSeries_iMXRTxxx):
            status, results, cmdStr = self.blhost.getProperty(boot.properties.kPropertyTag_CurrentVersion)
            return (status == boot.status.kStatus_Success)
        else:
            pass

    def jumpToFirmware( self ):
        if not self.isLoadFirmwareEnabled:
            return True
        firmwareBinFile = os.path.join(self.cpuDir, 'boot_firmware.bin')
        firmwareLoadAddr = self.tgt.firmwareLoadAddr
        firmwareJumpAddr = self.tgt.firmwareJumpAddr
        firmwareInitialSp = self.tgt.firmwareInitialSp
        if self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT10yy:
            status, results, cmdStr = self.sdphost.writeFile(firmwareLoadAddr, firmwareBinFile)
            if status != boot.status.kSDP_Status_HabEnabled and status != boot.status.kSDP_Status_HabDisabled:
                return False
            status, results, cmdStr = self.sdphost.jumpAddress(firmwareJumpAddr)
            if status != boot.status.kSDP_Status_HabEnabled and status != boot.status.kSDP_Status_HabDisabled:
                return False
        elif self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT11yy:
            status, results, cmdStr = self.blhost.loadImage(firmwareBinFile)
            if status != boot.status.kStatus_Success:
                return False
        elif self.tgt.mcuSeries == uidef.kMcuSeries_iMXRTxxx:
            status, results, cmdStr = self.blhost.writeMemory(firmwareLoadAddr, firmwareBinFile)
            if status != boot.status.kStatus_Success:
                return False
            #status, results, cmdStr = self.blhost.execute(firmwareJumpAddr, 0, firmwareInitialSp)
            #if status != boot.status.kStatus_Success:
            #    return False
        else:
            pass
        return True
