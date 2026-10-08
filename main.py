# -*- coding: utf-8 -*-
"""
main.py — VCam 组件启动与初始化逻辑参考实现
目标二进制: Vacm_afasds.dylib (arm64)

配套模块: hook_audio.py
本文件只覆盖【已静态证实】的启动路径；不包含推测性的 UI 布局或业务逻辑。

置信度图例
----------
[证实] 调用序列 / 选择子 / 参数形态直接来自所标注地址的反汇编。
[推断] 由调用序列 + 参数类型 + 数据流推导。
状态基址（0x3f61a0） 仍需运行时取值：0x3f61a0 等运行时填充槽位、
       0x27a584 等 7 个半字/分散写入目标（判定为二进制密钥而非字符串）。
       去混淆字符串本身已全部静态还原，见 strings_decoder.py。

启动链（已证实）
----------------
    __DATA_CONST,__mod_init_func  →  构造器
      └─ 0x276ed4  -[_0xA3F9c1E2 init]                    主控单例初始化 (3556 B)
           ├─ 0x276fdc..0x2774d4  运行时 XOR 去混淆 __DATA,__data 字符串表
           ├─ 0x277674 / 0x2776a0  宿主 App bundleIdentifier 白名单校验
           ├─ 0x2778d4            CIContext（软件渲染）
           ├─ 0x2779b0 / 0x2779d8  两个 dispatch_queue
           ├─ 0x277a04            NSLock（音频缓冲锁）
           ├─ 0x277a68            CMTimeMake(kCMTimeInvalid)
           └─ 0x277bd8 / 0x277c3c  两个 NSNotificationCenter 观察者

      └─ 0x28d490  -[_0x4B2d8E7F initPrivate]             悬浮菜单窗 (3536 B)
           ├─ 0x28d868 / 0x28d8c0  UIWindow 初始化
           ├─ 0x28dbe4            圆形按钮
           ├─ 0x28e044            长按手势
           ├─ 0x28e108            NSTimer 0.5s 循环
           └─ 0x28e160            setupMenuWindow
"""

import hook_audio
import strings_decoder as _sd

# menu.py 等模块经 vcam._deobf_string(addr) 取明文；静态已还原，无需运行时 hook。
deobf_string = _sd.deobf_string
read_cfstring = _sd.read_cfstring
PLAINTEXT_STRINGS = dict(_sd.PLAINTEXT)

# ---------------------------------------------------------------------------
# 真实地址常量
# ---------------------------------------------------------------------------

ADDR_VCAM_INIT                  = 0x276ED4   # -[_0xA3F9c1E2 init]        3556 B
ADDR_MENU_INIT_PRIVATE          = 0x28D490   # -[_0x4B2d8E7F initPrivate] 3536 B

ADDR_DEOBFUSCATE_START          = 0x276FDC   # XOR 去混淆循环起点
ADDR_DEOBFUSCATE_END            = 0x2774D4   # XOR 去混淆循环终点 (__bss 标志回写)
ADDR_HOST_CHECK_1               = 0x277674   # containsString:  (CFString @ 0x3f6828 → "tencent.xin")
ADDR_HOST_CHECK_2               = 0x2776A0   # containsString:  (CFString @ 0x3f68a8 → "wechat")
ADDR_HOST_FLAG_STORE            = 0x2776C4   # strb → __DATA,__common
ADDR_FILENAME_STORE             = 0x277734   # objc_storeStrong (CFString @ 0x3f67e8 → "B")
ADDR_CI_DICT                    = 0x2778D4   # dictionaryWithObjects:forKeys:count:
ADDR_CI_CONTEXT                 = 0x277904   # contextWithOptions:
ADDR_QUEUE_A                    = 0x2779B0   # dispatch_queue_create  (CI)
ADDR_QUEUE_B                    = 0x2779D8   # dispatch_queue_create  (音频)
ADDR_AUDIO_LOCK_ALLOC           = 0x277A04   # objc_alloc_init(NSLock)
ADDR_CMTIME_INVALID             = 0x277A68   # CMTimeMake(kCMTimeInvalid, ...)
ADDR_OBSERVER_1                 = 0x277BD8   # addObserver:selector:_0x6D9c3A1B:
ADDR_OBSERVER_2                 = 0x277C3C   # addObserver:selector:_0x9E4a5F8C:

ADDR_MENU_SUPER_WINDOWSCENE     = 0x28D868   # objc_msgSendSuper2 initWithWindowScene:
ADDR_MENU_SUPER_FRAME           = 0x28D8C0   # objc_msgSendSuper2 initWithFrame:
ADDR_MENU_SET_FRAME             = 0x28D99C   # setFrame:
ADDR_MENU_WINDOW_LEVEL          = 0x28D9D8   # setWindowLevel: (_UIWindowLevelNormal)
ADDR_MENU_CLEAR_COLOR           = 0x28D9FC   # [UIColor clearColor]
ADDR_MENU_BACKGROUND            = 0x28DA2C   # setBackgroundColor:
ADDR_MENU_USER_INTERACTION      = 0x28DA58   # setUserInteractionEnabled:
ADDR_MENU_TAG                   = 0x28DA78   # setTag:            (qword @ __TEXT,__const 0x34b780)
ADDR_MENU_ROOT_VC               = 0x28DA84   # objc_alloc_init(UIViewController)
ADDR_MENU_SET_ROOT_VC           = 0x28DBD4   # setRootViewController:
ADDR_MENU_BUTTON                = 0x28DBE4   # [UIButton buttonWithType:]
ADDR_MENU_SYSTEM_BLUE           = 0x28DCC0   # [UIColor systemBlueColor]
ADDR_MENU_ALPHA_COLOR           = 0x28DCE0   # colorWithAlphaComponent: 0.85 (f64 @ 0x34b728)
ADDR_MENU_CORNER_RADIUS         = 0x28DD7C   # setCornerRadius:        8.0  (fmov 立即数)
ADDR_MENU_CLIPS                 = 0x28DDB4   # setClipsToBounds:
ADDR_MENU_SET_TITLE             = 0x28DDE8   # setTitle:forState:        (CFString @ 0x3f61a0)
ADDR_MENU_BOLD_FONT             = 0x28DE00   # [UIFont boldSystemFontOfSize:]
ADDR_MENU_TITLE_LABEL           = 0x28DE3C   # titleLabel
ADDR_MENU_SET_FONT              = 0x28DE60   # setFont:
ADDR_MENU_NUM_LINES             = 0x28DEC0   # setNumberOfLines:        2    (mov 立即数)
ADDR_MENU_TEXT_ALIGN            = 0x28DF14   # setTextAlignment:        1    (mov 立即数)
ADDR_MENU_WHITE                 = 0x28DF58   # [UIColor whiteColor]
ADDR_MENU_TITLE_COLOR           = 0x28DF88   # setTitleColor:forState:
ADDR_MENU_BUTTON_TAPPED         = 0x28DFC8   # addTarget:action:@selector(buttonTapped)
ADDR_MENU_LONGPRESS             = 0x28E044   # initWithTarget:action:@selector(handleLongPress:)
ADDR_MENU_MIN_PRESS_DURATION    = 0x28E064   # setMinimumPressDuration:  0.2  (f64 @ 0x34b720)
ADDR_MENU_ADD_GESTURE           = 0x28E094   # addGestureRecognizer:
ADDR_MENU_STATUS_TIMER          = 0x28E114   # scheduledTimerWithTimeInterval:0.5 repeats:YES
ADDR_MENU_SETUP_WINDOW          = 0x28E160   # setupMenuWindow

# --- 从 __TEXT,__const 读出的实值（file offset == vmaddr）--------------------
CONST_MIN_PRESS_DURATION_ADDR  = 0x34B720   # <double> = 0.2
CONST_BUTTON_ALPHA_ADDR        = 0x34B728   # <double> = 0.85
CONST_WINDOW_TAG_ADDR           = 0x34B780   # <uint64> = 1447248205 = 0x56414C45 ("ELAV")

# 立即数（非内存加载）
IMMED_CORNER_RADIUS             = 8.0        # 0x28dd78  fmov d0, #8.00000000
IMMED_NUMBER_OF_LINES           = 2          # 0x28debc  mov x2, #2
IMMED_TEXT_ALIGNMENT            = 1          # 0x28df10  mov x2, #1  → NSTextAlignmentCenter
IMMED_TIMER_INTERVAL            = 0.5        # 0x28e10c  fmov d0, #0.50000000
IMMED_TIMER_REPEATS             = True       # 0x28e110  and w2, w8, #1


# ===========================================================================
# 1. 运行时字符串去混淆
# ===========================================================================
#
# [证实] init 的第一段（0x276fdc..0x2774d4）对 __DATA,__data 做一次性字节变换：
#
#   0x276f80  ldr  x8, [x8, #0x80]     → ___stack_chk_guard
#   0x276f94  ldar w8, [x8]            → 读 __DATA,__bss 的「已执行」标志
#   0x276fdc  ldrb w2, [x2, #0x6d0]    → 读混淆字节
#   0x276fe8  strb w2, [x3, #0x6d2]    → 写回（源/目标偏移不同 = 滚动复制）
#   0x277000  ldrb w13,[x13,#0x715]
#   0x277010  strb w13,[x2, #0x721]
#   0x2770bc  ldrb w12,[x12,#0x7a3]
#   0x2770cc  strb w12,[x1, #0x7aa]
#   0x277130  ldrb w11,[x11,#0x730]
#   0x277140  strb w11,[x16,#0x750]
#   0x277258  ldrb w15,[x15,#0x6e0]
#   0x277268  strb w15,[x17,#0x700]
#   0x27739c  ldrb w10,[x10,#0x770]
#   0x2773ac  strb w10,[x14,#0x790]
#   0x2774d4  stlr w9, [x10]           → 写回「已执行」标志 (__bss)
#
#   ldar/stlr 构成 dispatch_once 语义：整个解混淆只做一次。
#
# [证实] 解密块签名（15 处，全库唯一）：
#           adrp xN,#0x14e0000 / add xN,xN,#<flag> / ldar wR,[xN] / tbnz → 跳过
#           ldrb|ldrh|ldr  源 → eor(不同立即数) → strb|strh|str 目标（目标≠源）
#           stlr w9,[xN]  置位"已执行"
#         密钥为每个字节各自的立即数，非统一滚动序列；源密文在磁盘上不变。
#
# [证实] 早前记录的 4 个 CFString 地址整体偏移了 8 字节 —— 它们是 stride-32
#        CFConstantString 结构体本体，而非字符缓冲。结构体 = {isa, ptr, len, pad}，
#        按 ptr+len 读取后明文已完全闭合：
#
#          旧记 0x3f6820 → 实际 0x3f6828 → ptr 0x3f6721 len 11 → "tencent.xin"
#          旧记 0x3f68a0 → 实际 0x3f68a8 → ptr 0x3f67aa len  6 → "wechat"
#          旧记 0x3f67e0 → 实际 0x3f67e8 → ptr 0x3f66d2 len  1 → "B"
#          旧记 0x3f6860 → 实际 0x3f6868 → ptr 0x3f6790 len 18 → "VCamLicenseExpired"
#
#        len 字段 11 / 6 / 1 / 18 与结构体逐一吻合，0x3f61a0 全零（运行时填充槽位）。
#        完整实现见 strings_decoder.py；未闭合的半字/二进制目标见该文件「未闭合项」。
#
# 函数签名（逻辑等价表达）：
def deobfuscate_strings_once(flags):
    """0x276ed4 起始段 —— 一次性解密 15 个受保护缓冲。

    [证实] 明文已静态还原并固化于 strings_decoder.PLAINTEXT / CFSTRINGS，
           故本函数不再做内存变换，只按 ldar 语义置位各块标志。
    """
    return _sd.deobfuscate_strings_once(None, flags)


# [证实] 宿主白名单明文（0x277674 / 0x2776a0 两次 containsString:）
HOST_CHECK_S1 = _sd.HOST_CHECK_S1        # "tencent.xin"
HOST_CHECK_S2 = _sd.HOST_CHECK_S2        # "wechat"
LICENSE_NOTIFY_ADDR = _sd.LICENSE_NOTIFY_ADDR   # 0x3f6868
LICENSE_NOTIFY      = _sd.LICENSE_NOTIFY        # "VCamLicenseExpired"


# ===========================================================================
# 2. 宿主 App 白名单校验
# ===========================================================================
#
# [证实] 精确控制流（0x277660..0x2776c4）：
#
#   0x277660  ldr  x0, [x8]                    ; x0 = bundleIdentifier
#   0x277674  bl   objc_msgSend                ; [bundleId containsString: S1]  -> w0
#   0x277678  mov  w8, #1
#   0x27767c  stur w8, [x29,#-0xcc]            ; local = 1        <-- 默认放行
#   0x277680  tbnz w0, #0, #0x2776ac           ; S1 命中 → 直接跳到合并
#   0x277688  ldr  x0, [x8]                    ; 重新载入 bundleIdentifier
#   0x2776a0  bl   objc_msgSend                ; [bundleId containsString: S2]  -> w0
#   0x2776a4  stur w0, [x29,#-0xcc]            ; local = 结果2
#   0x2776a8  b    #0x2776ac
#   0x2776ac  ldur w8, [x29,#-0xcc]
#   0x2776b4  mov  w10, #1
#   0x2776c0  and  w8, w8, w10                 ; 归一化为 0/1
#   0x2776c4  strb w8, [x9]                    ; 写入 __DATA,__common 全局 BOOL
#
# 等价语义：
#     matched = True
#     if not bundle_id.containsString(S1):
#         matched = bundle_id.containsString(S2)
#     host_supported = bool(m
