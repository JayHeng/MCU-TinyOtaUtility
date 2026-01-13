#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import shutil
from . import memdef
sys.path.append(os.path.abspath(".."))
import boot
from run import runcore
from run import rundef
from ui import uidef
from ui import uivar
from ui import uilang
from utils import misc

class tinyOtaMem(runcore.tinyOtaRun):

    def __init__(self, parent):
        runcore.tinyOtaRun.__init__(self, parent)

        self.userFolder = os.path.join(self.exeTopRoot, 'gen', 'user_file')
        self.userFilename = os.path.join(self.userFolder, 'user.bin')

        self.memParamStatus = None
        self.memParamStart = None
        self.memParamLength = None
        self.memParamBinFile = None
        self.memParamDummyArg = None
        self.memParamUseFlashImageCmd = None

        self.otaMemStart = 0
        self.stage0BlFileTemp = os.path.join(self.userFolder, 'stage0Bl.bin')
        self.stage1BlFileTemp = os.path.join(self.userFolder, 'stage1Bl.bin')
        self.appSlot0FileTemp = os.path.join(self.userFolder, 'appSlot0.bin')
        self.appSlot1FileTemp = os.path.join(self.userFolder, 'appSlot1.bin')

    def getOneLineContentToShow( self, addr, memLeft, fileObj ):
        pad_bytes_before = addr % 16
        content_to_show = self.getFormattedUpperHexValue(addr - pad_bytes_before) + '    '
        to_read = min(16 - pad_bytes_before, int(memLeft) if memLeft is not None else 0)
        mem_content = fileObj.read(to_read) if to_read > 0 else b''
        if mem_content is None:
            mem_content = b''
        if isinstance(mem_content, (bytes, bytearray)):
            mem_bytes = bytearray(mem_content)
        else:
            mem_bytes = bytearray(mem_content)
        for i in range(16):
            if pad_bytes_before <= i < pad_bytes_before + len(mem_bytes):
                b = mem_bytes[i - pad_bytes_before]
                content_to_show += '{:02X} '.format(b)
            else:
                content_to_show += '-- '
        try:
            mem_content_bytes = bytes(mem_bytes)
        except TypeError:
            mem_content_bytes = ''.join(chr(x) for x in mem_bytes)
        return content_to_show, mem_content_bytes

    def getUserComMemParameters( self, isMemWrite=False ):
        status = False
        memStart = 0
        memLength = 0
        memBinFile = None
        memFlexibleArg = None
        useFlashImageCmd = False
        if isMemWrite:
            memBinFile = self.getComMemBinFile()
            if not os.path.isfile(memBinFile):
                status = False
            else:
                memFlexibleArg = memBinFile
                extType = os.path.splitext(memBinFile)[-1]
                if (extType in memdef.kAppImageFileExtensionList_S19) or \
                   (extType in memdef.kAppImageFileExtensionList_Hex):
                    useFlashImageCmd = True
                    status = True
                else:
                    status, memStart = self.getComMemStartAddress()
        else:
            status, memStart = self.getComMemStartAddress()
            if status:
                status, memFlexibleArg = self.getComMemByteLength()

        self.memParamStatus = status
        self.memParamStart = memStart
        self.memParamLength = memFlexibleArg
        self.memParamBinFile = memFlexibleArg
        self.memParamDummyArg = useFlashImageCmd
        self.memParamUseFlashImageCmd = useFlashImageCmd

    def _convertComMemStart( self, memStart ):
        if memStart < self.tgt.flexspiNorMemBase:
            memStart += self.tgt.flexspiNorMemBase
        return memStart

    def convertComMemEraseUnit( self, memEraseUnit ):
        eraseUnit = self.tgt.xspiNorEraseAlignment
        if eraseUnit != None:
            if eraseUnit < memEraseUnit:
                eraseUnit = memEraseUnit
        else:
            eraseUnit = memEraseUnit
        return eraseUnit

    def readXspiFlashMemory( self ):
        #status, memStart, memLength, dummyArg = self.getUserComMemParameters(False)
        status = self.memParamStatus
        memStart = self.memParamStart
        memLength = self.memParamLength
        dummyArg = self.memParamDummyArg
        if status:
            memStart = self._convertComMemStart(memStart)
            alignedMemStart = misc.align_down(memStart, self.comMemReadUnit)
            alignedMemLength = misc.align_up(memLength, self.comMemReadUnit)
            if memLength + memStart > alignedMemStart + alignedMemLength:
                alignedMemLength += self.comMemReadUnit
            memFilename = 'commonDataFromBootDevice.dat'
            memFilepath = os.path.join(self.blhostVectorsDir, memFilename)
            status, results, cmdStr = self.blhost.readMemory(alignedMemStart, alignedMemLength, memFilename, rundef.kBootDeviceMemId_FlexspiNor)
            if status == boot.status.kStatus_Success:
                self.clearMem()
                memLeft = memLength
                addr = memStart
                with open(memFilepath, 'rb') as fileObj:
                    fileObj.seek(memStart - alignedMemStart)
                    while memLeft > 0:
                        contentToShow, memContent = self.getOneLineContentToShow(addr, memLeft, fileObj)
                        memLeft -= len(memContent)
                        addr += len(memContent)
                        self.printMem(contentToShow)
            else:
                self.popupMsgBox('Failed to read Flash, error code is %d !' %(status))

    def eraseXspiFlashMemory( self ):
        #status, memStart, memLength, dummyArg = self.getUserComMemParameters(False)
        status = self.memParamStatus
        memStart = self.memParamStart
        memLength = self.memParamLength
        dummyArg = self.memParamDummyArg
        if status:
            memStart = self._convertComMemStart(memStart)
            memEraseUnit = self.convertComMemEraseUnit(self.comMemEraseUnit)
            alignedMemStart = misc.align_down(memStart, memEraseUnit)
            alignedMemLength = misc.align_up(memLength, memEraseUnit)
            if memLength + memStart > alignedMemStart + alignedMemLength:
                alignedMemLength += memEraseUnit
            status, results, cmdStr = self.blhost.flashEraseRegion(alignedMemStart, alignedMemLength, rundef.kBootDeviceMemId_FlexspiNor)
            if status != boot.status.kStatus_Success:
                self.popupMsgBox('Failed to erase Flash, error code is %d !' %(status))

    def massEraseXspiFlashMemory( self ):
        status, results, cmdStr = self.blhost.flashEraseAll(rundef.kBootDeviceMemId_FlexspiNor)
        if status != boot.status.kStatus_Success:
            self.popupMsgBox('Failed to mass erase Flash, error code is %d !' %(status))

    def writeXspiFlashMemory( self ):
        #status, memStart, memBinFile, useFlashImageCmd = self.getUserComMemParameters(True)
        status = self.memParamStatus
        memStart = self.memParamStart
        memBinFile = self.memParamBinFile
        useFlashImageCmd = self.memParamUseFlashImageCmd
        if status:
            if useFlashImageCmd:
                memBinFilepath, memBinfilename = os.path.split(memBinFile)
                userFormatFile = os.path.join(self.userFolder, memBinfilename)
                shutil.copy(memBinFile, userFormatFile)
                status, results, cmdStr = self.blhost.flashImage(userFormatFile, 'erase', rundef.kBootDeviceMemId_FlexspiNor)
                try:
                    os.remove(userFormatFile)
                except:
                    pass
                if status != boot.status.kStatus_Success:
                    self.popupMsgBox('Failed to write Flash, error code is %d, double check image address first!' %(status))
            else:
                memStart = self._convertComMemStart(memStart)
                memEraseUnit = self.convertComMemEraseUnit(self.comMemEraseUnit)
                if memStart % self.comMemWriteUnit:
                    self.popupMsgBox('Start Address should be aligned with 0x%x !' %(self.comMemWriteUnit))
                    return
                eraseMemStart = misc.align_down(memStart, memEraseUnit)
                eraseMemEnd = misc.align_up(memStart + os.path.getsize(memBinFile), memEraseUnit)
                status, results, cmdStr = self.blhost.flashEraseRegion(eraseMemStart, eraseMemEnd - eraseMemStart, rundef.kBootDeviceMemId_FlexspiNor)
                if status != boot.status.kStatus_Success:
                    self.popupMsgBox('Failed to erase Flash, error code is %d !' %(status))
                    return
                shutil.copy(memBinFile, self.userFilename)
                status, results, cmdStr = self.blhost.writeMemory(memStart, self.userFilename, rundef.kBootDeviceMemId_FlexspiNor)
                try:
                    os.remove(self.userFilename)
                except:
                    pass
                if status != boot.status.kStatus_Success:
                    self.popupMsgBox('Failed to write Flash, error code is %d, You may forget to erase Flash first!' %(status))

    def makeOtaFile( self, fileType = 'stage1Bl' ):
        if fileType == uidef.kOtaFileType_S1BL:
            pass
        elif fileType == uidef.kOtaFileType_APP0:
            shutil.copy(self.appSlot0File, self.appSlot0FileTemp)
            self.replaceWordInFile(self.appSlot0FileTemp, memdef.kImageHeaderWordOffset_Length, os.path.getsize(self.appSlot0FileTemp))
            self.replaceWordInFile(self.appSlot0FileTemp, memdef.kImageHeaderWordOffset_AuthType, memdef.kImageAuthType_CRC32)
            self.replaceWordInFile(self.appSlot0FileTemp, memdef.kImageHeaderWordOffset_Crc32, 0x0)
            self.replaceWordInFile(self.appSlot0FileTemp, memdef.kImageHeaderWordOffset_Magic, memdef.kImageHeaderMagicWord_App)
        elif fileType == uidef.kOtaFileType_APP1:
            shutil.copy(self.appSlot1File, self.appSlot1FileTemp)
            self.replaceWordInFile(self.appSlot1FileTemp, memdef.kImageHeaderWordOffset_Length, os.path.getsize(self.appSlot1FileTemp))
            self.replaceWordInFile(self.appSlot1FileTemp, memdef.kImageHeaderWordOffset_AuthType, memdef.kImageAuthType_CRC32)
            self.replaceWordInFile(self.appSlot1FileTemp, memdef.kImageHeaderWordOffset_Crc32, 0x0)
            self.replaceWordInFile(self.appSlot1FileTemp, memdef.kImageHeaderWordOffset_Magic, memdef.kImageHeaderMagicWord_App)
        else:
            return

    def downloadOtaFile( self, fileType = 'stage0Bl' ):
        memStart = self.otaMemStart
        if fileType == uidef.kOtaFileType_S0BL:
            memBinFile = self.stage0BlFile
            tempMemFile = self.stage0BlFileTemp
        elif fileType == uidef.kOtaFileType_S1BL:
            memBinFile = self.stage1BlFile
            tempMemFile = self.stage1BlFileTemp
        elif fileType == uidef.kOtaFileType_APP0:
            memBinFile = self.appSlot0File
            tempMemFile = self.appSlot0FileTemp
        elif fileType == uidef.kOtaFileType_APP1:
            memBinFile = self.appSlot1File
            tempMemFile = self.appSlot1FileTemp
        else:
            return
        if os.path.isfile(memBinFile) and memStart != None:
            memStart = self._convertComMemStart(memStart)
            memEraseUnit = self.convertComMemEraseUnit(self.comMemEraseUnit)
            if memStart % self.comMemWriteUnit:
                self.popupMsgBox('Start Address should be aligned with 0x%x !' %(self.comMemWriteUnit))
                return
            eraseMemStart = misc.align_down(memStart, memEraseUnit)
            eraseMemEnd = misc.align_up(memStart + os.path.getsize(memBinFile), memEraseUnit)
            status, results, cmdStr = self.blhost.flashEraseRegion(eraseMemStart, eraseMemEnd - eraseMemStart, rundef.kBootDeviceMemId_FlexspiNor)
            if status != boot.status.kStatus_Success:
                self.popupMsgBox('Failed to erase Flash, error code is %d !' %(status))
                return
            if not os.path.isfile(tempMemFile):
                shutil.copy(memBinFile, tempMemFile)
            status, results, cmdStr = self.blhost.writeMemory(memStart, tempMemFile, rundef.kBootDeviceMemId_FlexspiNor)
            try:
                os.remove(tempMemFile)
            except:
                pass
            if status != boot.status.kStatus_Success:
                self.popupMsgBox('Failed to download file into Flash, error code is %d, You may forget to erase Flash first!' %(status))
