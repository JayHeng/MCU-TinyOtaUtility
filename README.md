----
　　Tiny OTA 是一个针对 i.MX RT 系列的 OTA 参考设计，其包含 MCU 端固件（tota_sbl 和 tota_app）和 PC 端 GUI 工具（MCU-TinyOtaUtility）两部分。  

![](./doc/v1.0/block_diagram.png)

　　tota_sbl 是示例 bootloader 程序，其由 MCU ROM 引导启动，该程序负责检查 OTA 标志、校验两个 Slot 位置的 tota_app 完整性并选择高版本跳转执行，其也支持通过 blhost 协议与上位机通信以更新 tota_app。  

　　tota_app 是示例 application 程序，其就是一个基于 SDK hello world XIP 工程的模板，用户可以基于此模板开发自己的应用。无论 Slot 0 还是 Slot 1 位置的 application 均共享同一个链接文件（即永远被搬移到 Slot 0 位置处运行）。  

　　MCU-TinyOtaUtility 是基于 PyQT5 的上位机工具，其支持 tota_sbl 和 tota_app 的加 OTA 头操作，还能与 MCU ROM 进行通信以实现 tota_sbl 和 tota_app 的烧写，同时也支持对 Flash 进行一般读写擦操作。  

### 一、特性概述

Tiny OTA 工具：

```text
1. 支持i.MXRT117x
2. 支持i.MXRT118x
3. 支持NOR Flash一般读写擦操作
4. 支持UART&USB blhost协议与MCU ROM通信
5. 支持bootloader程序加头(slot0,1 app start, Magic)与下载
6. 支持application程序加头(Len, CRC32, Version, Magic)与下载
```

Tiny OTA 固件：

```text
1. 支持i.MXRT117x
2. 支持i.MXRT118x
4. 支持主核示例程序（对于双核MCU而言）
4. BL: 仅支持FlexSPI1 XIP application程序管理 (永远从slot 0位置启动)
5. BL: 支持CRC32-MPEG2校验以判断application完整性
6. BL: 复用软件reliable update流程(来自于Kinetis Bootloader)
7. BL: 5秒超时内通过UART&USB blhost与上位机通信，否则跳转进application执行
```

### 二、MCU端固件

```text
固件地址 https://github.com/JayHeng/imxrt-tiny-ota-fw/archive/refs/tags/v1.0.zip
IDE版本：IAR EWARM v9.70.1
```

#### 2.1 tota_app
　　使用 IAR 打开 \imxrt-tiny-ota-fw\targets\imxrt1180\apps\tota_app\cm33 工程（基于SDK hello world XIP 工程），切换到 flex_nor_debug target（工程选项里已经设置了 XIP_BOOT_HEADER_ENABLE=0，即生成的 binary 就是裸的 ARM 程序），当前在其链接文件里设定 ARM 程序起始地址在 FlexSPI1 Flash 的 0x28080000 处，编译生成 tota_app_cm33.bin（bin 起始地址就是 0x28080000），用户可根据需要修改 tota_app 工程链接文件里的 app_image_offset 值。  

```text
define symbol m_flash_start            = 0x28000000;
define symbol app_image_offset         = 0x00080000;
define symbol m_text_start             = m_flash_start + app_image_offset;
```

![](./doc/v1.0/rt1180_tota_app_proj.png)

　　有了 tota_app_cm33.bin 之后，后续再通过 MCU-TinyOtaUtility 工具加上 OTA 头（包含 Length、CRC32、Version、Magic）并将其烧写到 Flash Slot0 或者 Slot1 位置（注意 Slot 0 对应偏移应与 app_image_offset 一致），OTA 信息位置复用了 ARM Vector Table 里保留的如下几个 Vector。  

![](./doc/v1.0/app_image_header.png)

#### 2.2 tota_sbl
　　使用 IAR 打开 \imxrt-tiny-ota-fw\targets\imxrt1180\apps\tota_sbl\cm33 工程（基于SDK flashloader 工程，但是对工程做了一些改动，增加了 ROM boot header，链接文件也从 RAM target 改成了标准 XIP target，此外还使能了黑科技，即利用 IDE 特性将除了 init_data_bss 代码之外的 RO 段全部搬移到 RAM 执行，这样方便运行后续因 application 搬移需要的 Flash 擦写操作），当前在其链接文件里设定 ARM 程序起始地址在 FlexSPI1 Flash 的 0x2800B000 处，编译生成 tota_sbl_cm33.bin（注意 bin 起始地址是 0x28000400，因为包含 fcb 等启动头），一般来说我们无需修改 tota_sbl 工程链接文件。  

```text
define symbol m_flash_start            = 0x28000000;
define symbol app_image_offset         = 0x0000B000;
define symbol m_text_start             = m_flash_start + app_image_offset;

define symbol m_fcb_offset             = 0x400;
define symbol m_fcb_start              = m_flash_start + m_fcb_offset;

define symbol m_interrupts_ram_start   = 0x304A0000;
```

　　因为 RT1180 独特的 TRDC 权限管理，在 tota_sbl 工程配套的 container 里的 image_entry.size 长度需要覆盖从 Flash 起始地址一直覆盖到 Slot 0 全部空间，否则会影响 ROM 跳转至 tota_sbl 以及 tota_sbl 跳转到 tota_app 执行。这一点后续可改进为在 tota_sbl 里设置 TRDC 权限来解决 tota_app 跳转权限问题，这样可以减小 container 里的 image_entry.size 长度（仅需覆盖 tota_sbl 空间即可）。  

![](./doc/v1.0/rt1180_tota_sbl_proj.png)

　　有了 tota_sbl_cm33.bin 之后，后续再通过 MCU-TinyOtaUtility 工具加上 OTA 头（包含 slot0,1 app start, Magic）并将其烧写到 Flash 起始位置（从 fcb 位置开始），OTA 信息位置依然复用了 ARM Vector Table 里保留的如下几个 Vector。这里的 app load addr 参数功能暂时还未实现，后续可用于拓展支持灵活的 application 加载地址配置。  

![](./doc/v1.0/sbl_image_header.png)

　　当 Flash Slot 0,1 处分别有了可用的 application，为了调试方便，我们也可以直接手动修改 tota_sbl 工程的 startup 文件里的如下参数值，这样可以直接在线下载调试 tota_sbl 工程，无需通过上位机工具来添加 OTA 头以及烧写。  

![](./doc/v1.0/rt1180_tota_sbl_proj2.png)

#### 2.3 SBL里Reliable Update流程
　　当 SBL 里 OTA 头 Magic 校验通过，且 slot 0,1 地址有效时，SBL 会执行 Reliable Update 流程。

```text
1. 如果 slot 0,1 程序均无效（无 Magic 或者 CRC 校验失败），直接进入 ISP 模式等待上位机下载
2. 如果 slot 0 程序有效，slot 1 程序无效，5s 超时后跳转至 slot 0 程序执行
3. 如果 slot 0 程序无效，slot 1 程序有效，将 slot 1 程序拷贝至 slot 0 位置，5s 超时后跳转至 slot 0 程序执行
4. 如果 slot 0,1 程序均有效，判断两者的程序版本：
  - 如果 slot 0 版本不低于 slot 1 版本，5s 超时后跳转至 slot 0 程序执行
  - 如果 slot 0 版本低于 slot 1 版本，将 slot 1 程序拷贝至 slot 0 位置，5s 超时后跳转至 slot 0 程序执行
```

### 三、PC端GUI工具

```text
工具地址 https://github.com/JayHeng/MCU-TinyOtaUtility/archive/refs/tags/v1.0.zip
```

#### 3.1 建立连接
　　双击 \MCU-TinyOtaUtility\bin\MCU-TinyOtaUtility.exe 打开工具，根据目标板 Flash 连接情况做相应设置，将 RT1180-EVK 开发板启动模式设置为 ISP 模式，然后连接上 UART 或者 USB cable，点击 'Connect' 按钮可在左下角信息框里看到连接信息。  

![](./doc/v1.0/tool_connect.png)

#### 3.2 OTA下载
　　准备好了 tota_sbl_cm33.bin 以及 tota_app_cm33.bin 之后，可先点击界面篮圈指示里 'Stage1 BL File', 'Slot0/1 App File' 按钮分别指向对应的路径，这里 Slot0/1 可用同一个 application binary 文件。然后设置红框里的 'start' 以及 'version' 参数，这里 Stage1 BL 对应的偏移 0x400，以及 Slot0 App 对应的偏移 0x80000 应与对应工程链接文件设置匹配，而 Slot1 App 对应的偏移位置可自由设置；至于 Version 设置，目前最大支持 V255.255 即 2bytes 存储。设置好了之后，最后点击 'All In One' 按钮即可完成三个文件的 OTA 头添加以及下载（也可分步操作）。  

![](./doc/v1.0/tool_ota.png)

　　下载完成之后将 RT1180-EVK 开发板启动模式设置为 Flash Boot 模式，打开串口调试助手可看如下打印信息，这里设置的 slot 1 版本高于 slot 0，所以我们看到 sbl 将 slot 1 app 拷贝到了 slot 0 位置并跳转执行。  

![](./doc/v1.0/ota_res.png)

#### 3.3 一般Flash操作
　　成功建立连接之后，可对 Flash 指定范围进行一般读写擦操作，注意当前写操作仅支持 binary 文件格式（.bin）。  

![](./doc/v1.0/tool_flash_ewr.png)

