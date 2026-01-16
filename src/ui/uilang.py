#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2022 NXP
# All rights reserved.
# 
# SPDX-License-Identifier: BSD-3-Clause

import sys
import os

kMenuPosition_File     = 0x0
kMenuPosition_Edit     = 0x1
kMenuPosition_View     = 0x2
kMenuPosition_Tools    = 0x3
kMenuPosition_Window   = 0x4
kMenuPosition_Help     = 0x5

kRevision_1_0_0_en =  "【v1.0.0】 \n" + \
                      "  Feature: \n" + \
                      "     1. Support i.MXRT117x \n" + \
                      "     2. Support i.MXRT118x \n" + \
                      "     3. Support NOR Flash R/W/E Operation \n" + \
                      "     4. Support UART&USB ISP via ROM \n" + \
                      "     5. Support bl image making(solt0,1 app start) and downloading \n" + \
                      "     6. Support XIP app image making(CRC32, Version) and downloading\n\n"

kMsgLanguageContentDict = {
        'homePage_title':                     ['Home Page'],
        'homePage_info':                      ['https://github.com/JayHeng/MCU-TinyOtaUtility.git \n'],
        'aboutAuthor_title':                  ['About Author'],
        'aboutAuthor_author':                 [u"Author: 痞子衡 \n"],
        'aboutAuthor_email1':                 ['Email: jie.heng@nxp.com \n'],
        'aboutAuthor_email2':                 ['Email: hengjie1989@foxmail.com \n'],
        'aboutAuthor_blog':                   [u"Blog: 痞子衡嵌入式 https://www.cnblogs.com/henjay724/ \n"],
        'revisionHistory_title':              ['Revision History'],
        'revisionHistory_v1_0_0':             [kRevision_1_0_0_en],

        'connectError_doubleCheckBmod':       ['Make sure that you have put MCU in UART SDP mode (BMOD[1:0] pins = 2\'b01)!'],
        'connectError_failToJumpToFl':        ['MCU has entered ROM SDP mode but failed to jump to Flashloader, Please reset board and try again!'],
        'connectError_failToPingFl':          ['Failed to ping Flashloader, Please reset board and consider updating flashloader.srec file under /src/targets/ then try again!'],
        'connectError_failToCfgBootDevice':   ['MCU has entered Flashloader but failed to configure Flash memory!'],
        'connectError_hasnotCfgBootDevice':   ['Please configure Flash via Flashloader first!'],
        'connectError_hasnotEnterFl':         ['Please connect to Flashloader first!'],
        'connectError_InvalidBootableFl':     ['Cannot find bootable flashloader file!'],
}