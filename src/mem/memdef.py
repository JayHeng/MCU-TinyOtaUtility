import sys, os

kAppImageFileExtensionList_Elf = ['.out', '.elf', '.axf']
kAppImageFileExtensionList_S19 = ['.srec', '.s19', '.mot', '.mxt', '.m32', '.s28', '.s37']
kAppImageFileExtensionList_Hex = ['.hex']
kAppImageFileExtensionList_Bin = ['.bin']

kImageAuthType_NonxipCRC32  = 0x0002
kImageAuthType_XipCRC32     = 0x0005

kImageHeaderWordOffset_Magic    = 7
kImageHeaderWordOffset_Length   = 8
kImageHeaderWordOffset_AuthType = 9
kImageHeaderWordOffset_Crc32    = 10
kImageHeaderWordOffset_LoadAddr = 13
kImageHeaderMagicWord_App    =0x50504154 #0x54 ('T'), 0x41 ('A'), 0x50 ('P'), 0x50 ('P')

kImageHeaderWordOffset_App0LoadAddr = 8
kImageHeaderWordOffset_App1LoadAddr = 9
kImageHeaderWordOffset_AppLoadAddr  = 10
kImageHeaderMagicWord_Boot   =0x4C425354 #0x54 ('T'), 0x53 ('S'), 0x42 ('B'), 0x4C ('L')
