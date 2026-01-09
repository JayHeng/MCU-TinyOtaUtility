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
        self.mcuDeviceHabStatus = None
        self.bootDeviceMemBase = None
        self.comMemWriteUnit = 0x1
        self.comMemEraseUnit = 0x1
        self.comMemReadUnit = 0x1
        self.createMcuTarget()

    def createMcuTarget( self ):
        self.tgt, self.cpuDir = createTarget(self.mcuDevice, self.exeBinRoot)

    def getUsbid( self ):
        self.createMcuTarget()
        return [self.tgt.romUsbVid, self.tgt.romUsbPid, self.tgt.flashloaderUsbVid, self.tgt.flashloaderUsbPid]

    def connectToDevice( self , connectStage):
        if connectStage == uidef.kConnectStage_Rom:
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
            if self.isUartPortSelected:
                xPeripheral = xhost + 'uart'
                uartComPort = self.uartComPort
                uartBaudrate = int(self.uartBaudrate)
                usbVid = ''
                usbPid = ''
            elif self.isUsbhidPortSelected:
                xPeripheral = xhost + 'usb'
                uartComPort = ''
                uartBaudrate = ''
                usbVid = self.tgt.romUsbVid
                usbPid = self.tgt.romUsbPid
            else:
                pass
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
        elif connectStage == uidef.kConnectStage_Flashloader:
            if self.isUartPortSelected:
                blPeripheral = 'uart'
                uartComPort = self.uartComPort
                uartBaudrate = int(self.uartBaudrate)
                usbVid = ''
                usbPid = ''
            elif self.isUsbhidPortSelected:
                blPeripheral = 'usb'
                uartComPort = ''
                uartBaudrate = ''
                usbVid = self.tgt.flashloaderUsbVid
                usbPid = self.tgt.flashloaderUsbPid
            else:
                pass
            self.blhost = bltest.createBootloader(self.tgt,
                                                  self.blhostVectorsDir,
                                                  blPeripheral,
                                                  uartBaudrate, uartComPort,
                                                  usbVid, usbPid,
                                                  True)
        elif connectStage == uidef.kConnectStage_Reset:
            self.tgt = None
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

    def _formatBootloaderVersion( self, version):
        identifier0 = chr((version & 0xff000000) >> 24)
        identifier1 = str((version & 0xff0000) >> 16)
        identifier2 = str((version & 0xff00) >> 8)
        identifier3 = str(version & 0xff)
        return identifier0 + identifier1 + '.' + identifier2 + '.' + identifier3

    def getMcuDeviceBootloaderVersion( self ):
        status, results, cmdStr = self.blhost.getProperty(boot.properties.kPropertyTag_CurrentVersion)
        if status == boot.status.kStatus_Success:
            self.printDeviceStatus('Current Version  = ' + self._formatBootloaderVersion(results[0]))
        else:
            pass
        status, results, cmdStr = self.blhost.getProperty(boot.properties.kPropertyTag_TargetVersion)
        if status == boot.status.kStatus_Success:
            self.tgt.romTargetVersion = results[0] & rundef.kRomTargetVersionMainMask
            self.printDeviceStatus('Target Version   = ' + self._formatBootloaderVersion(results[0]))
        else:
            pass

    def getMcuDeviceBootloaderUniqueId( self ):
        status, results, cmdStr = self.blhost.getProperty(boot.properties.kPropertyTag_UniqueDeviceIdent)
        if status == boot.status.kStatus_Success:
            self.printDeviceStatus('Unique ID[31:00] = ' + self.convertLongIntHexText(str(hex(results[0]))))
            self.printDeviceStatus('Unique ID[63:32] = ' + self.convertLongIntHexText(str(hex(results[1]))))
            try:
                self.printDeviceStatus('Unique ID[95:64] = ' + self.convertLongIntHexText(str(hex(results[2]))))
                self.printDeviceStatus('Unique ID[127:96] = ' + self.convertLongIntHexText(str(hex(results[3]))))
            except:
                pass
        else:
            pass

    def getMcuDeviceInfoViaRom( self ):
        self.printDeviceStatus("--------MCU Device ROM Info--------")
        if self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT10yy:
            # RT10yy supports SDP protocol, but some device(RT1011) doesn't support Read Register command
            pass
        elif self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT11yy:
            # RT11yy doesn't support SDP protocol
            self.getMcuDeviceBootloaderUniqueId()
            self.getMcuDeviceBootloaderVersion()

    def getMcuDeviceHabStatus( self ):
        if self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT10yy:
            pass
        elif self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT11yy:
            status, results, cmdStr = self.blhost.getProperty(boot.properties.kPropertyTag_FlashSecurityState)
            if status == boot.status.kStatus_Success:
                if results[0] == 0:
                    self.mcuDeviceHabStatus = rundef.kHabStatus_Open
                    self.printDeviceStatus('Life Cycle status = HAB Open')
                else:
                    self.mcuDeviceHabStatus = rundef.kHabStatus_Closed0
                    self.printDeviceStatus('Life Cycle status = HAB Closed')
            else:
                pass
        else:
            pass

    def _selectFlashloader( self ):
        flBinFile = None
        flLoadAddr = None
        flJumpAddr = None
        if self.tgt.bootHeaderType == rundef.kBootHeaderType_IVT:
            flBinFile = os.path.join(self.cpuDir, 'ivt_flashloader.bin')
        elif self.tgt.bootHeaderType == rundef.kBootHeaderType_Container:
            if (self.tgt.flexspiNorMemBase >> 28) % 2:
                flBinFile = os.path.join(self.cpuDir, 'cntr_flashloader_s.bin')
            else:
                flBinFile = os.path.join(self.cpuDir, 'cntr_flashloader_ns.bin')
        else:
            pass
        flLoadAddr = self.tgt.flashloaderLoadAddr
        flJumpAddr = self.tgt.flashloaderJumpAddr
        return flBinFile, flLoadAddr, flJumpAddr

    def jumpToFlashloader( self ):
        flashloaderBinFile, flashloaderLoadAddr, flashloaderJumpAddr = self._selectFlashloader()
        if flashloaderBinFile == None:
            self.popupMsgBox(uilang.kMsgLanguageContentDict['connectError_InvalidBootableFl'])
            return False
        if self.mcuDeviceHabStatus == rundef.kHabStatus_Closed0 or self.mcuDeviceHabStatus == rundef.kHabStatus_Closed1:
            return False
        elif self.mcuDeviceHabStatus == rundef.kHabStatus_FAB or self.mcuDeviceHabStatus == rundef.kHabStatus_Open:
            pass
        else:
            pass
        if self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT10yy:
            status, results, cmdStr = self.sdphost.writeFile(flashloaderLoadAddr, flashloaderBinFile)
            if status != boot.status.kSDP_Status_HabEnabled and status != boot.status.kSDP_Status_HabDisabled:
                return False
            status, results, cmdStr = self.sdphost.jumpAddress(flashloaderJumpAddr)
            if status != boot.status.kSDP_Status_HabEnabled and status != boot.status.kSDP_Status_HabDisabled:
                return False
        elif self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT11yy:
            status, results, cmdStr = self.blhost.loadImage(flashloaderBinFile)
            if status != boot.status.kStatus_Success:
                return False
        else:
            pass
        return True

    def pingFlashloader( self ):
        status, results, cmdStr = self.blhost.getProperty(boot.properties.kPropertyTag_CurrentVersion)
        return (status == boot.status.kStatus_Success)

    def getMcuDeviceInfoViaFlashloader( self ):
        self.printDeviceStatus("--------MCU Flashloader Info---------")
        self.getMcuDeviceBootloaderVersion()

    def updateXspiNorMemBase( self ):
        if self.xspiInstance == 0:
            self.tgt.flexspiNorMemBase = self.tgt.flexspiNorMemBase0
        elif self.xspiInstance == 1:
            self.tgt.flexspiNorMemBase = self.tgt.flexspiNorMemBase1
        else:
            pass

    def setXspiInstance( self ):
        if self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT10yy:
            pass
        elif self.tgt.mcuSeries == uidef.kMcuSeries_iMXRT11yy:
            # In RT1170 flashloader, 0xFC900001/0xFC900002 is used to switch FlexSPI instance
            #  0xFC900001 -> Primary instance
            #  0xFC900002 -> Secondary instance
            configOpt = rundef.kFlexspiDevCfgInfo_Instance + self.xspiInstance
            status = boot.status.kStatus_Success
            status, results, cmdStr = self.blhost.fillMemory(self.tgt.ramFreeSpaceStart_LoadCommOpt, 0x4, configOpt)
            if status != boot.status.kStatus_Success:
                return False
            status, results, cmdStr = self.blhost.configureMemory(rundef.kBootDeviceMemId_FlexspiNor, self.tgt.ramFreeSpaceStart_LoadCommOpt)
            if status != boot.status.kStatus_Success:
                return False
        else:
            pass

    def configureBootDevice ( self ):
        configOptList = []
        self.updateXspiNorMemBase()
        self.updateXspiNorOptValue()
        configOptList.extend([self.xspiNorOpt0, self.xspiNorOpt1])
        self.setXspiInstance()
        status = boot.status.kStatus_Success
        for i in range(len(configOptList)):
            status, results, cmdStr = self.blhost.fillMemory(self.tgt.ramFreeSpaceStart_LoadCommOpt + 4 * i, 0x4, configOptList[i])
            if status != boot.status.kStatus_Success:
                return False
        status, results, cmdStr = self.blhost.configureMemory(rundef.kBootDeviceMemId_FlexspiNor, self.tgt.ramFreeSpaceStart_LoadCommOpt)
        return (status == boot.status.kStatus_Success)

    def showAsOptimalMemoryUnit( self, memSizeBytes ):
        strMemSize = ''
        if memSizeBytes >= 0x40000000:
            strMemSize = str(memSizeBytes * 1.0 / 0x40000000) + ' GB'
        elif memSizeBytes >= 0x100000:
            strMemSize = str(memSizeBytes * 1.0 / 0x100000) + ' MB'
        elif memSizeBytes >= 0x400:
            strMemSize = str(memSizeBytes * 1.0 / 0x400) + ' KB'
        else:
            strMemSize = str(memSizeBytes) + ' Bytes'
        return strMemSize

    def getVal32FromBinFile( self, filename, offset=0):
        var32Value = 0
        if os.path.isfile(filename):
            with open(filename, 'rb') as f:
                f.seek(offset)
                b = f.read(4)
                if len(b) != 4:
                    return 0
            var32Value = (b[3] << 24) + (b[2] << 16) + (b[1] << 8) + b[0]
        return var32Value

    def _getFlexspiNorDeviceInfo ( self, useDefault=False ):
        filename = 'flexspiNorCfg.dat'
        filepath = os.path.join(self.blhostVectorsDir, filename)
        status, results, cmdStr = self.blhost.readMemory(self.tgt.flexspiNorMemBase + self.tgt.xspiNorCfgInfoOffset, self.tgt.xspiNorCfgInfoLen, filename, rundef.kBootDeviceMemId_FlexspiNor)
        if status != boot.status.kStatus_Success:
            return False
        flexspiTag = self.getVal32FromBinFile(filepath, rundef.kFlexspiNorCfgOffset_FlexspiTag)
        if flexspiTag == rundef.kFlexspiNorCfgTag_Flexspi:
            pageByteSize = self.getVal32FromBinFile(filepath, rundef.kFlexspiNorCfgOffset_PageByteSize)
            sectorByteSize = self.getVal32FromBinFile(filepath, rundef.kFlexspiNorCfgOffset_SectorByteSize)
            blockByteSize = self.getVal32FromBinFile(filepath, rundef.kFlexspiNorCfgOffset_BlockByteSize)
            self.printDeviceStatus("Page Size   = " + self.showAsOptimalMemoryUnit(pageByteSize))
            self.printDeviceStatus("Sector Size = " + self.showAsOptimalMemoryUnit(sectorByteSize))
            self.printDeviceStatus("Block Size  = " + self.showAsOptimalMemoryUnit(blockByteSize))
            if pageByteSize != 0 and pageByteSize != 0xffffffff:
                self.comMemWriteUnit = pageByteSize
                self.comMemReadUnit = pageByteSize
            if sectorByteSize != 0 and sectorByteSize != 0xffffffff:
                self.comMemEraseUnit = sectorByteSize
            if blockByteSize != 0 and blockByteSize != 0xffffffff:
                if self.isInfineonMirrorBitDevice():
                    self.comMemEraseUnit = blockByteSize
        else:
            if not useDefault:
                self.printDeviceStatus("Page Size   = --------")
                self.printDeviceStatus("Sector Size = --------")
                self.printDeviceStatus("Block Size  = --------")
                return False
            else:
                pageByteSize = rundef.kXspiNorDefaultMemInfo_PageSize
                sectorByteSize = rundef.kXspiNorDefaultMemInfo_SectorSize
                blockByteSize = rundef.kXspiNorDefaultMemInfo_BlockSize
                self.printDeviceStatus("Page Size   = * " + self.showAsOptimalMemoryUnit(pageByteSize))
                self.printDeviceStatus("Sector Size = * " + self.showAsOptimalMemoryUnit(sectorByteSize))
                self.printDeviceStatus("Block Size  = * " + self.showAsOptimalMemoryUnit(blockByteSize))
                self.printDeviceStatus("Note: Cannot get correct FDCB, just use default memory info here")
                self.comMemWriteUnit = pageByteSize
                self.comMemEraseUnit = sectorByteSize
                self.comMemReadUnit = pageByteSize
        try:
            os.remove(filepath)
        except:
            pass
        return True

    def getBootDeviceInfoViaFlashloader ( self ):
        self.printDeviceStatus("----------xSPI NOR memory-----------")
        if not self._getFlexspiNorDeviceInfo(False):
            self.printDeviceStatus("Flash is configured but without FDCB")

    def resetMcuDevice( self ):
        status, results, cmdStr = self.blhost.reset()
        return (status == boot.status.kStatus_Success)