# -*- coding: utf-8 -*-
"""
main.py — VCam 组件启动与初始化。

覆盖主控单例 _0xA3F9c1E2 的 init，以及悬浮菜单窗 _0x4B2d8E7F 的 initPrivate。
"""

import hook_audio
import strings_decoder as _sd

deobf_string      = _sd.deobf_string
read_cfstring     = _sd.read_cfstring
PLAINTEXT_STRINGS = dict(_sd.PLAINTEXT)

# ---------------------------------------------------------------------------
# 常量地址
# ---------------------------------------------------------------------------
ADDR_VCAM_INIT         = 0x276ED4
ADDR_MENU_INIT_PRIVATE = 0x28D490

ADDR_DEOBFUSCATE_START = 0x276FDC
ADDR_DEOBFUSCATE_END   = 0x2774D4
ADDR_HOST_CHECK_1      = 0x277674
ADDR_HOST_CHECK_2      = 0x2776A0
ADDR_HOST_FLAG_STORE   = 0x2776C4
ADDR_FILENAME_STORE    = 0x277734
ADDR_CI_DICT           = 0x2778D4
ADDR_CI_CONTEXT        = 0x277904
ADDR_QUEUE_A           = 0x2779B0
ADDR_QUEUE_B           = 0x2779D8
ADDR_AUDIO_LOCK_ALLOC  = 0x277A04
ADDR_CMTIME_INVALID    = 0x277A68
ADDR_OBSERVER_1        = 0x277BD8
ADDR_OBSERVER_2        = 0x277C3C

ADDR_MENU_SUPER_WINDOWSCENE = 0x28D868
ADDR_MENU_SUPER_FRAME       = 0x28D8C0
ADDR_MENU_SET_FRAME         = 0x28D99C
ADDR_MENU_WINDOW_LEVEL      = 0x28D9D8
ADDR_MENU_CLEAR_COLOR       = 0x28D9FC
ADDR_MENU_BACKGROUND        = 0x28DA2C
ADDR_MENU_USER_INTERACTION  = 0x28DA58
ADDR_MENU_TAG               = 0x28DA78
ADDR_MENU_ROOT_VC           = 0x28DA84
ADDR_MENU_SET_ROOT_VC       = 0x28DBD4
ADDR_MENU_BUTTON            = 0x28DBE4
ADDR_MENU_SYSTEM_BLUE       = 0x28DCC0
ADDR_MENU_ALPHA_COLOR       = 0x28DCE0
ADDR_MENU_CORNER_RADIUS     = 0x28DD7C
ADDR_MENU_CLIPS             = 0x28DDB4
ADDR_MENU_SET_TITLE         = 0x28DDE8
ADDR_MENU_BOLD_FONT         = 0x28DE00
ADDR_MENU_TITLE_LABEL       = 0x28DE3C
ADDR_MENU_SET_FONT          = 0x28DE60
ADDR_MENU_NUM_LINES         = 0x28DEC0
ADDR_MENU_TEXT_ALIGN        = 0x28DF14
ADDR_MENU_WHITE             = 0x28DF58
ADDR_MENU_TITLE_COLOR       = 0x28DF88
ADDR_MENU_BUTTON_TAPPED     = 0x28DFC8
ADDR_MENU_LONGPRESS         = 0x28E044
ADDR_MENU_MIN_PRESS_DURATION = 0x28E064
ADDR_MENU_ADD_GESTURE       = 0x28E094
ADDR_MENU_STATUS_TIMER      = 0x28E114
ADDR_MENU_SETUP_WINDOW      = 0x28E160

CONST_MIN_PRESS_DURATION_ADDR = 0x34B720
CONST_BUTTON_ALPHA_ADDR       = 0x34B728
CONST_WINDOW_TAG_ADDR         = 0x34B780

IMMED_CORNER_RADIUS   = 8.0
IMMED_NUMBER_OF_LINES = 2
IMMED_TEXT_ALIGNMENT  = 1
IMMED_TIMER_INTERVAL  = 0.5
IMMED_TIMER_REPEATS   = True


def deobfuscate_strings_once(flags):
    """一次性解密受保护缓冲；明文已固化，仅按 ldar 语义置位各块标志。"""
    return _sd.deobfuscate_strings_once(None, flags)


HOST_CHECK_S1       = _sd.HOST_CHECK_S1
HOST_CHECK_S2       = _sd.HOST_CHECK_S2
LICENSE_NOTIFY_ADDR = _sd.LICENSE_NOTIFY_ADDR
LICENSE_NOTIFY      = _sd.LICENSE_NOTIFY


# ---------------------------------------------------------------------------
# 宿主白名单校验
# ---------------------------------------------------------------------------
HOST_CHECK_S1_ADDR = 0x3F6828
HOST_CHECK_S2_ADDR = 0x3F68A8
FILENAME_CHAR_ADDR = 0x3F67E8
FILENAME_CHAR      = "B"


def check_host_supported(runtime):
    """判断当前宿主 App 是否在白名单内；结果写入全局 BOOL。"""
    bundle    = runtime.objc_msgSend("_OBJC_CLASS_$_NSBundle", "mainBundle")
    bundle_id = runtime.objc_msgSend(bundle, "bundleIdentifier")

    matched = True
    if not runtime.objc_msgSend(bundle_id, "containsString:", HOST_CHECK_S1_ADDR):
        matched = runtime.objc_msgSend(bundle_id, "containsString:", HOST_CHECK_S2_ADDR)

    runtime.store_common_bool("host_supported", bool(matched))
    return bool(matched)


# ---------------------------------------------------------------------------
# 主控单例
# ---------------------------------------------------------------------------
class VCamController:
    """_0xA3F9c1E2 —— 全局主控单例。"""

    def __init__(self, runtime):
        self.rt = runtime
        self.name = "_0xA3F9c1E2"

    def init(self):
        deobfuscate_strings_once(self.rt)
        self.rt.objc_msgSendSuper2(self, "init")

        if not check_host_supported(self.rt):
            pass

        fm = self.rt.objc_msgSend("_OBJC_CLASS_$_NSFileManager", "defaultManager")
        self.file_name_char = FILENAME_CHAR_ADDR
        self.file_manager   = fm

        self.original_imps = hook_audio.AudioImpRegistry(self.rt)

        self.ci_options = self.rt.objc_msgSend(
            "_OBJC_CLASS_$_NSDictionary",
            "dictionaryWithObjects:forKeys:count:",
            [self.rt.number_with_bool(False),
             self.rt.number_with_bool(True),
             self.rt.number_with_bool(True)],
            ["kCIContextUseSoftwareRenderer",
             "kCIContextCacheIntermediates",
             "kCIContextPriorityRequestLow"],
            3)
        self.ci_context = self.rt.objc_msgSend(
            "_OBJC_CLASS_$_CIContext", "contextWithOptions:", self.ci_options)

        self.ci_queue    = self.rt.dispatch_queue_create(None)
        self.audio_queue = self.rt.dispatch_queue_create(None)

        self.audio_lock = self.rt.objc_alloc_init("_OBJC_CLASS_$_NSLock")

        self.last_pts_invalid = True
        self.rt.store_common_bool("has_valid_pts", False)

        self.zero_size = self.rt.cg_size_zero()

        nc = self.rt.objc_msgSend("_OBJC_CLASS_$_NSNotificationCenter", "defaultCenter")
        self.rt.objc_msgSend(nc, "addObserver:selector:name:object:",
                             self, "_0x6D9c3A1B:", None, None)
        self.rt.objc_msgSend(nc, "addObserver:selector:name:object:",
                             self, "_0x9E4a5F8C:", LICENSE_NOTIFY_ADDR, None)
        return self

    # ---- 便捷转发 ----
    @property
    def shared(self):
        return self.rt.shared_instance(self.name)

    def audio_inject_enabled(self):
        return self.rt.bool_ivar("audioInjectEnabled")

    def set_audio_inject_enabled_(self, value):
        self.rt.set_bool_ivar("audioInjectEnabled", bool(value))

    def cached_audio_buffer(self):
        return self.rt.obj_ivar("cachedAudioBuffer")

    def set_cached_audio_buffer_(self, buf):
        self.rt.set_obj_ivar("cachedAudioBuffer", buf)

    def clear_audio_buffer(self):
        with self.audio_lock:
            old = self.cached_audio_buffer()
            self.set_cached_audio_buffer_(None)
            if old is not None:
                self.rt.CFRelease(old)

    def is_audio_hooked_(self, class_name):
        return self.original_imps.is_audio_hooked(class_name)

    def get_original_audio_imp_(self, class_name):
        return self.original_imps.get(class_name)

    def set_original_audio_imp_(self, imp, class_name):
        self.original_imps.set(imp, class_name)


# ---------------------------------------------------------------------------
# 悬浮菜单窗
# ---------------------------------------------------------------------------
class FloatingMenuWindow:
    """_0x4B2d8E7F —— 悬浮控制菜单。"""

    def __init__(self, runtime):
        self.rt = runtime
        self.name = "_0x4B2d8E7F"

    def init_private(self):
        deobfuscate_strings_once(self.rt)

        scene = self.rt.current_window_scene()
        self.rt.objc_msgSendSuper2(self, "initWithWindowScene:", scene)
        self.rt.objc_msgSendSuper2(self, "initWithFrame:", self.rt.cg_rect_zero())
        self.rt.objc_msgSendSuper2(self, "initWithFrame:", self.rt.cg_rect_zero())

        self.rt.objc_msgSend(self, "setFrame:", self.rt.cg_rect_zero())
        self.rt.objc_msgSend(self, "setWindowLevel:",
                             self.rt.symbol("_UIWindowLevelNormal"))

        clear = self.rt.objc_msgSend("_OBJC_CLASS_$_UIColor", "clearColor")
        self.rt.objc_msgSend(self, "setBackgroundColor:", clear)
        self.rt.objc_msgSend(self, "setUserInteractionEnabled:", True)
        self.rt.objc_msgSend(self, "setTag:", self.rt.read_uint64(CONST_WINDOW_TAG_ADDR))

        self.root_vc = self.rt.objc_alloc_init("_OBJC_CLASS_$_UIViewController")
        self.rt.objc_msgSend(self, "setRootViewController:", self.root_vc)

        button = self.rt.objc_msgSend("_OBJC_CLASS_$_UIButton",
                                      "buttonWithType:", 0)

        blue  = self.rt.objc_msgSend("_OBJC_CLASS_$_UIColor", "systemBlueColor")
        alpha = self.rt.read_double(CONST_BUTTON_ALPHA_ADDR)
        blue_alpha = self.rt.objc_msgSend(blue, "colorWithAlphaComponent:", alpha)

        layer = self.rt.objc_msgSend(button, "layer")
        self.rt.objc_msgSend(layer, "setCornerRadius:", IMMED_CORNER_RADIUS)
        self.rt.objc_msgSend(button, "setClipsToBounds:", True)
        self.rt.objc_msgSend(button, "setBackgroundColor:", blue_alpha)
        self.rt.objc_msgSend(button, "setTitle:forState:", 0x3F61A0, 0)

        font = self.rt.objc_msgSend("_OBJC_CLASS_$_UIFont",
                                    "boldSystemFontOfSize:", IMMED_CORNER_RADIUS)
        title_label = self.rt.objc_msgSend(button, "titleLabel")
        self.rt.objc_msgSend(title_label, "setFont:", font)
        self.rt.objc_msgSend(title_label, "setNumberOfLines:", IMMED_NUMBER_OF_LINES)
        self.rt.objc_msgSend(title_label, "setTextAlignment:", IMMED_TEXT_ALIGNMENT)

        white = self.rt.objc_msgSend("_OBJC_CLASS_$_UIColor", "whiteColor")
        self.rt.objc_msgSend(button, "setTitleColor:forState:", white, 0)

        self.rt.objc_msgSend(button, "addTarget:action:forControlEvents:",
                             self, "buttonTapped", 0x7)

        lp = self.rt.objc_msgSend("_OBJC_CLASS_$_UILongPressGestureRecognizer", "alloc")
        lp = self.rt.objc_msgSend(lp, "initWithTarget:action:",
                                  self, "handleLongPress:")
        self.rt.objc_msgSend(lp, "setMinimumPressDuration:",
                             self.rt.read_double(CONST_MIN_PRESS_DURATION_ADDR))
        self.rt.objc_msgSend(self, "addGestureRecognizer:", lp)

        self.status_timer = self.rt.objc_msgSend(
            "_OBJC_CLASS_$_NSTimer",
            "scheduledTimerWithTimeInterval:repeats:block:",
            IMMED_TIMER_INTERVAL, IMMED_TIMER_REPEATS,
            self.rt.make_block(self._on_status_tick))

        self.rt.objc_msgSend(self, "setupMenuWindow")
        return self

    def _on_status_tick(self):
        pass

    def mute_tapped(self):
        return hook_audio.mute_tapped(self.rt)

    def audio_inject_tapped(self):
        return hook_audio.audio_inject_tapped(self.rt)


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------
def bootstrap(runtime):
    controller = VCamController(runtime).init()
    hook_audio.bind(vcam_shared=controller.shared,
                    queue_audio=controller.audio_queue)
    menu = FloatingMenuWindow(runtime).init_private()
    return controller, menu


if __name__ == "__main__":
    raise SystemExit(__doc__)
