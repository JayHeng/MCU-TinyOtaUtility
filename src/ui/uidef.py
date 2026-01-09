
# Copyright 2022 NXP
# All rights reserved.
# 
# SPDX-License-Identifier: BSD-3-Clause

import sys, os

kConnectStage_Rom            = 1
kConnectStage_Flashloader    = 2
kConnectStage_ExternalMemory = 3
kConnectStage_Reset          = 4

kMcuSeries_iMXRT10yy = 'RT10yy'
kMcuSeries_iMXRT11yy = 'RT11yy'

kMcuSeries_iMXRTyyyy = [kMcuSeries_iMXRT10yy, kMcuSeries_iMXRT11yy]
kMcuSeries_iMXRTxxx  = 'RTxxx'

kMcuDevice_iMXRT500  = 'i.MXRT5xx'
kMcuDevice_iMXRT500S = 'i.MXRT5xxS'
kMcuDevice_iMXRT600  = 'i.MXRT6xx'
kMcuDevice_iMXRT600S = 'i.MXRT6xxS'
kMcuDevice_iMXRT700  = 'i.MXRT7xx'
kMcuDevice_iMXRTxxx = [kMcuDevice_iMXRT500, kMcuDevice_iMXRT600, kMcuDevice_iMXRT700]

kMcuDevice_iMXRT1011 = 'i.MXRT1011'
kMcuDevice_iMXRT1015 = 'i.MXRT1015'
kMcuDevice_iMXRT102x = 'i.MXRT1021'
kMcuDevice_iMXRT1024 = 'i.MXRT1024 SIP'
kMcuDevice_iMXRT105x = 'i.MXRT105x'
kMcuDevice_iMXRT106x = 'i.MXRT106x'
kMcuDevice_iMXRT1064 = 'i.MXRT1064 SIP'
kMcuDevice_iMXRT10yy = [kMcuDevice_iMXRT1011, kMcuDevice_iMXRT1015, kMcuDevice_iMXRT102x, kMcuDevice_iMXRT1024, kMcuDevice_iMXRT105x, kMcuDevice_iMXRT106x, kMcuDevice_iMXRT1064]

kMcuDevice_iMXRT116x = 'i.MXRT116x'
kMcuDevice_iMXRT117x = 'i.MXRT117x'
kMcuDevice_iMXRT118x = 'i.MXRT118x'
kMcuDevice_iMXRT11yy = [kMcuDevice_iMXRT116x, kMcuDevice_iMXRT117x, kMcuDevice_iMXRT118x]

kMcuDevice_v1_0       = [kMcuDevice_iMXRT117x, kMcuDevice_iMXRT118x]
kMcuDevice_Latest     = kMcuDevice_iMXRTxxx + kMcuDevice_iMXRT10yy + kMcuDevice_iMXRT11yy

kFlexspiNorDevice_Winbond_W25Q128JV     = 'W25QxxxJV'
kFlexspiNorDevice_Winbond_W35T51NW      = 'W35T51NW'
kFlexspiNorDevice_MXIC_MX25L12845G      = 'MX25Lxxx45G'
kFlexspiNorDevice_MXIC_MX25UM51245G     = 'MX25UM51245G'
kFlexspiNorDevice_MXIC_MX25UM51345G     = 'MX25UM51345G'
kFlexspiNorDevice_MXIC_MX25UM51345G_OPI = 'MX25UM51345G_Def_OPI_DDR'
kFlexspiNorDevice_MXIC_MX25UM51345G_2nd = 'MX25UM51345G_2ndPinmux'
kFlexspiNorDevice_GigaDevice_GD25Q64C   = 'GD25QxxxC'
kFlexspiNorDevice_GigaDevice_GD25LB256E = 'GD25LBxxxE'
kFlexspiNorDevice_GigaDevice_GD25LT256E = 'GD25LTxxxE'
kFlexspiNorDevice_GigaDevice_GD25LX256E = 'GD25LXxxxE'
kFlexspiNorDevice_ISSI_IS25LP064A       = 'IS25LPxxxA'
kFlexspiNorDevice_ISSI_IS25LX256        = 'IS25LXxxx'
kFlexspiNorDevice_ISSI_IS26KS512S       = 'IS26KSxxxS'
kFlexspiNorDevice_Micron_MT25QL128A     = 'MT25QLxxxA'
kFlexspiNorDevice_Micron_MT35X_RW303    = 'RW303-MT35XUxxxABA1G'
kFlexspiNorDevice_Micron_MT35X_RW304    = 'RW304-MT35XUxxxABA2G_Def_OPI_DDR'
kFlexspiNorDevice_Adesto_AT25SF128A     = 'AT25SFxxxA'
kFlexspiNorDevice_Adesto_ATXP032        = 'ATXPxxx'
kFlexspiNorDevice_Cypress_S25FL064L     = 'S25FLxxxL'
kFlexspiNorDevice_Cypress_S25FL128S     = 'S25FLxxxS'
kFlexspiNorDevice_Cypress_S28HS512T     = 'S28HSxxxT'
kFlexspiNorDevice_Cypress_S26KS512S     = 'S26KSxxxS'

kFlexspiNorOpt0_Winbond_W25Q128JV     = 0xc0000207
kFlexspiNorOpt0_Winbond_W35T51NW      = 0xc0603005
kFlexspiNorOpt0_MXIC_MX25L12845G      = 0xc0000007
kFlexspiNorOpt0_MXIC_MX25UM51245G     = 0xc0403037
kFlexspiNorOpt0_MXIC_MX25UM51345G     = 0xc0403007
kFlexspiNorOpt0_MXIC_MX25UM51345G_OPI = 0xc0433007
kFlexspiNorOpt0_MXIC_MX25UM51345G_2nd = 0xc1503051
kFlexspiNorOpt1_MXIC_MX25UM51345G_2nd = 0x20000014
kFlexspiNorOpt0_GigaDevice_GD25Q64C   = 0xc0000406
kFlexspiNorOpt0_GigaDevice_GD25LB256E = 0xc0000007
kFlexspiNorOpt0_GigaDevice_GD25LT256E = 0xc0000008
kFlexspiNorOpt0_GigaDevice_GD25LX256E = 0xc0603008
kFlexspiNorOpt0_ISSI_IS25LP064A       = 0xc0000007
kFlexspiNorOpt0_ISSI_IS25LX256        = 0xC0603005
kFlexspiNorOpt0_ISSI_IS26KS512S       = 0xc0233007
kFlexspiNorOpt0_Micron_MT25QL128A     = 0xc0000007
kFlexspiNorOpt0_Micron_MT35X_RW303    = 0xC0603005
kFlexspiNorOpt0_Micron_MT35X_RW304    = 0xC0633005
kFlexspiNorOpt0_Adesto_AT25SF128A     = 0xc0000007
kFlexspiNorOpt0_Adesto_ATXP032        = 0xc0803007
kFlexspiNorOpt0_Cypress_S25FL064L     = 0xc0000007
kFlexspiNorOpt0_Cypress_S25FL128S     = 0xc0000007
kFlexspiNorOpt0_Cypress_S28HS512T     = 0xc0A03007
kFlexspiNorOpt0_Cypress_S26KS512S     = 0xc0233007

kAdvancedSettings_Tool             = 0

kButtonColor_Enable  = "rgb(142,229,238)"
kButtonColor_Disable = "rgb(248,248,255)"

