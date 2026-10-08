# -*- coding: utf-8 -*-
"""
menu.py — 悬浮菜单窗口 _0x4B2d8E7F（UIWindow 子类）。
"""

from __future__ import annotations

from video_inject import (
    MENU_TAG,
    MENU_ALPHA_CONST,
    MENU_ALPHA_CONST_ADDR,
    LONG_PRESS_MIN,
    LONG_PRESS_MIN_ADDR,
    LONG_PRESS_MENU,
    CORNER_RADIUS_BY_CALLSITE,
    ALPHA_BY_CALLSITE,
)


TIMER_INTERVAL = 0.5


# ---------------------------------------------------------------------------
# initPrivate
# ---------------------------------------------------------------------------
def init_private(vcam):
    vcam._deobfuscate_once(0x28d4d8, 0x28d560)

    if vcam._has_window_scene():
        self_ = vcam.objc_msgSendSuper2(vcam.self_class,
                                        "initWithWindowScene:", vcam.window_scene)
    else:
        self_ = vcam.objc_msgSendSuper2(vcam.self_class,
                                        "initWithFrame:", vcam.MENU_TAG)

    vcam.objc_msgSend(self_, "setFrame:", vcam.MENU_TAG)
    vcam.objc_msgSend(self_, "setWindowLevel:", vcam.UIWindowLevelNormal)

    clear = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "clearColor")
    vcam.objc_msgSend(self_, "setBackgroundColor:", clear)
    vcam.objc_msgSend(self_, "setUserInteractionEnabled:", True)
    vcam.objc_msgSend(self_, "setTag:", MENU_TAG)

    vc = vcam.alloc_init(vcam.CLASS_UIVIEWCONTROLLER)
    root = vcam.objc_msgSend(vc, "view")
    vcam.objc_msgSend(vc, "setRootViewController:", self_)
    _ = root

    btn  = vcam.objc_msgSend(vcam.CLASS_UIBUTTON, "buttonWithType:",
                             vcam.UIButtonTypeCustom)
    tint = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "systemBlueColor")
    tint = vcam.objc_msgSend(tint, "colorWithAlphaComponent:", 0.5)
    vcam.objc_msgSend(btn, "setBackgroundColor:", tint)

    lay = vcam.objc_msgSend(btn, "layer")
    vcam.objc_msgSend(lay, "setCornerRadius:", CORNER_RADIUS_BY_CALLSITE[0x28dd78])
    vcam.objc_msgSend(lay, "setClipsToBounds:", True)

    vcam.objc_msgSend(btn, "setTitle:forState:", vcam.HANDLE_TITLE, 0)
    font  = vcam.objc_msgSend(vcam.CLASS_UIFONT, "boldSystemFontOfSize:",
                              vcam.HANDLE_FONT_SIZE)
    label = vcam.objc_msgSend(btn, "titleLabel")
    vcam.objc_msgSend(label, "setFont:", font)
    vcam.objc_msgSend(label, "setNumberOfLines:", 2)
    vcam.objc_msgSend(label, "setTextAlignment:", 1)

    white = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "whiteColor")
    vcam.objc_msgSend(label, "setTitleColor:forState:", white, 0)

    vcam.objc_msgSend(btn, "addTarget:action:forControlEvents:",
                      self_, "buttonTapped", vcam.UIControlEventTouchUpInside)

    lp = vcam.alloc_init(vcam.CLASS_UILONGPRESS)
    vcam.objc_msgSend(lp, "initWithTarget:action:", self_, "handleLongPress:")
    vcam.objc_msgSend(lp, "setMinimumPressDuration:", LONG_PRESS_MIN)
    vcam.objc_msgSend(self_, "addGestureRecognizer:", lp)

    timer = vcam.objc_msgSend(vcam.CLASS_NSTIMER,
                              "scheduledTimerWithTimeInterval:repeats:block:",
                              TIMER_INTERVAL, True,
                              lambda: vcam.objc_msgSend(self_, "setupMenuWindow"))
    vcam.objc_msgSend(self_, "setStatusTimer:", timer)
    return self_


# ---------------------------------------------------------------------------
# setupMenuWindow
# ---------------------------------------------------------------------------
def setup_menu_window(vcam):
    screen = vcam.objc_msgSend(vcam.CLASS_UISCREEN, "mainScreen")
    bounds = vcam.objc_msgSend(screen, "bounds")

    win = vcam.alloc_init(vcam.self_class)
    vcam.objc_msgSend(win, "setFrame:", bounds)
    vcam.objc_msgSend(win, "setWindowLevel:", vcam.UIWindowLevelNormal)

    clear = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "clearColor")
    vcam.objc_msgSend(win, "setBackgroundColor:", clear)
    vcam.objc_msgSend(win, "setHidden:", True)
    vcam.objc_msgSend(win, "setTag:", MENU_TAG)

    vc = vcam.alloc_init(vcam.CLASS_UIVIEWCONTROLLER)
    container = vcam.objc_msgSend(vc, "view")
    vcam.objc_msgSend(vc, "setRootViewController:", win)
    vcam.objc_msgSend(container, "setFrame:",
                      vcam.objc_msgSend(container, "frame"))
    vcam.objc_msgSend(container, "addSubview:", win)

    buttons = (
        ("selectImageBtn",  "selectImageTapped"),
        ("selectVideoBtn",  "selectVideoTapped"),
        ("networkBtn",      "networkTapped"),
        ("mirrorBtn",       "mirrorTapped"),
        ("muteBtn",         "muteTapped"),
        ("audioInjectBtn",  "audioInjectTapped"),
        ("rotateBtn",       "rotateTapped"),
        ("disableBtn",      "disableTapped"),
    )
    for getter, action in buttons:
        btn = vcam.objc_msgSend(win, getter)
        vcam.objc_msgSend(btn, "addTarget:action:forControlEvents:",
                          win, action, vcam.UIControlEventTouchUpInside)

    lp = vcam.alloc_init(vcam.CLASS_UILONGPRESS)
    vcam.objc_msgSend(lp, "initWithTarget:action:", win, "_0x4F7a1B3E:")
    vcam.objc_msgSend(lp, "setMinimumPressDuration:", LONG_PRESS_MENU)
    vcam.objc_msgSend(win, "addGestureRecognizer:", lp)

    tap = vcam.alloc_init(vcam.CLASS_UITAP)
    vcam.objc_msgSend(tap, "initWithTarget:action:", win, "backgroundTapped:")
    vcam.objc_msgSend(win, "addGestureRecognizer:", tap)
    return win


# ---------------------------------------------------------------------------
# 交互转发
# ---------------------------------------------------------------------------
def background_tapped(vcam, self_, recognizer):
    pt  = vcam.objc_msgSend(recognizer, "locationInView:", vcam.self)
    box = vcam.objc_msgSend(vcam.self, "bounds")
    if vcam.CGRectContainsPoint(box, pt):
        return False
    vcam.objc_msgSend(vcam.self, "toggleMenu")
    return True


def button_tapped(vcam, self_):
    vcam.objc_msgSend(vcam.self, "toggleMenu")


def toggle_menu(vcam, self_):
    visible = not vcam._ivar_is_menu_visible(self_)
    vcam._set_ivar_is_menu_visible(self_, visible)
    if visible:
        vcam.objc_msgSend(vcam._ivar_menu_window(self_), "setAlpha:",
                          ALPHA_BY_CALLSITE[0x28ffe4])
    else:
        vcam.objc_msgSend(vcam._ivar_menu_window(self_), "setAlpha:",
                          ALPHA_BY_CALLSITE[0x290074])


# ---------------------------------------------------------------------------
# 状态刷新
# ---------------------------------------------------------------------------
def refresh_status(vcam, self_):
    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")

    can_image = vcam.objc_msgSend(shared, "_0x9D4e6F2B:", vcam.SOURCE_IMAGE)
    vcam.objc_msgSend(vcam._ivar_select_image_btn(self_), "setEnabled:", can_image)

    can_video = vcam.objc_msgSend(shared, "_0x9D4e6F2B:", vcam.SOURCE_VIDEO)
    vcam.objc_msgSend(vcam._ivar_select_video_btn(self_), "setAlpha:",
                      1.0 if can_video else 0.5)

    can_net = vcam.objc_msgSend(shared, "_0x3B8f1D5E")
    vcam.objc_msgSend(vcam._ivar_network_btn(self_), "setEnabled:", can_net)

    can_audio_inject = vcam.objc_msgSend(shared, "_0x6C8d1E3F")
    vcam.objc_msgSend(vcam._ivar_audio_inject_btn(self_), "setEnabled:",
                      can_audio_inject)

    can_mirror = vcam.objc_msgSend(shared, "_0x9D4e6F2B:", vcam.FEATURE_MIRROR)
    vcam.objc_msgSend(vcam._ivar_mirror_btn(self_), "setEnabled:", can_mirror)

    label = vcam._ivar_status_label(self_)
    info  = vcam.objc_msgSend(shared, "currentVideoInfo")
    if info is None:
        text  = vcam._deobf_string(0x290254)
        color = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "grayColor")
    else:
        text  = vcam._deobf_string(0x2902cc)
        color = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "systemGreenColor")
    vcam.objc_msgSend(label, "setText:", text)
    vcam.objc_msgSend(label, "setTextColor:", color)

    _paint_toggle(vcam, self_, "mirrorBtn",
                  lambda: vcam.objc_msgSend(shared, "frontCameraMirrorEnabled"),
                  lambda v: vcam.objc_msgSend(shared, "setFrontCameraMirrorEnabled:", v),
                  vcam.CLASS_UICOLOR, "systemGreenColor")

    _paint_toggle(vcam, self_, "muteBtn",
                  lambda: vcam.objc_msgSend(shared, "audioMuted"),
                  lambda v: vcam.objc_msgSend(shared, "setAudioMuted:", v),
                  vcam.CLASS_UICOLOR, "systemOrangeColor")

    _paint_toggle(vcam, self_, "audioInjectBtn",
                  lambda: vcam.objc_msgSend(shared, "audioInjectEnabled"),
                  lambda v: vcam.objc_msgSend(shared, "setAudioInjectEnabled:", v),
                  vcam.CLASS_UICOLOR, "systemGreenColor")

    deg   = vcam.objc_msgSend(shared, "rotationDegree")
    title = vcam.objc_msgSend(vcam.CLASS_NSSTRING, "stringWithFormat:",
                              vcam.ROTATE_FORMAT, deg)
    vcam.objc_msgSend(vcam._ivar_rotate_btn(self_), "setTitle:forState:", title, 0)


def _paint_toggle(vcam, self_, btn_getter, get_flag, set_flag, color_cls, on_name):
    btn = vcam.objc_msgSend(self_, btn_getter)
    if get_flag():
        title = vcam._deobf_string_on()
        on_color = vcam.objc_msgSend(color_cls, on_name)
        bg = vcam.objc_msgSend(on_color, "colorWithAlphaComponent:", 0.3)
        vcam.objc_msgSend(btn, "setBackgroundColor:", bg)
        vcam.objc_msgSend(btn, "setTitle:forState:", title, 0)
        vcam.objc_msgSend(btn, "setTitleColor:forState:",
                          vcam.objc_msgSend(color_cls, "darkGrayColor"), 0)
    else:
        title = vcam._deobf_string_off()
        gray = vcam.objc_msgSend(color_cls, "systemGrayColor")
        bg = vcam.objc_msgSend(gray, "colorWithAlphaComponent:", 0.3)
        vcam.objc_msgSend(btn, "setBackgroundColor:", bg)
        vcam.objc_msgSend(btn, "setTitleColor:forState:",
                          vcam.objc_msgSend(color_cls, "darkGrayColor"), 0)


# ---------------------------------------------------------------------------
# 各功能按钮
# ---------------------------------------------------------------------------
def select_image_tapped(vcam, self_):
    vcam.objc_msgSend(self_, "toggleMenu")


def select_video_tapped(vcam, self_):
    vcam.objc_msgSend(self_, "toggleMenu")


def network_tapped(vcam, self_):
    vcam.objc_msgSend(self_, "toggleMenu")

    app = vcam.objc_msgSend(vcam.CLASS_UIAPPLICATION, "sharedApplication")
    host = None
    for w in vcam._enumerate(vcam.objc_msgSend(app, "windows")):
        if vcam.objc_msgSend(vcam.objc_msgSend(w, "class"),
                             "isKindOfClass:", vcam.CLASS_UIWINDOW):
            if not vcam.objc_msgSend(w, "isHidden"):
                vc = vcam.objc_msgSend(w, "rootViewController")
                if vc is not None:
                    host = vc
                    break
    if host is None:
        return None

    for vc in vcam._enumerate(vcam.objc_msgSend(app, "windows")):
        root = vcam.objc_msgSend(vc, "rootViewController")
        if root is not None:
            host = root
            break
    top = vcam.objc_msgSend(host, "presentedViewController")
    while top is not None:
        host = top
        top = vcam.objc_msgSend(host, "presentedViewController")

    alert = vcam.objc_msgSend(vcam.CLASS_UIALERTCONTROLLER,
                              "alertControllerWithTitle:message:preferredStyle:",
                              vcam.NET_ALERT_TITLE,
                              vcam.NET_ALERT_MESSAGE,
                              vcam.UIAlertControllerStyleAlert)
    vcam.objc_msgSend(host, "presentViewController:animated:completion:",
                      alert, True, None)

    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    return vcam.objc_msgSend(shared, "_0x4E7a2B9D:", alert)


def mirror_tapped(vcam, self_):
    if not vcam.objc_msgSend(vcam.CLASS_A3F9C1E2,
                             "_0x9D4e6F2B:", vcam.FEATURE_MIRROR):
        vcam.objc_msgSend(self_, "showFeatureDisabledTip")
        return False
    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    cur = vcam.objc_msgSend(shared, "frontCameraMirrorEnabled")
    vcam.objc_msgSend(shared, "setFrontCameraMirrorEnabled:", not cur)
    vcam.objc_msgSend(self_, "_0xA14d5E7F")
    return True


def mute_tapped(vcam, self_):
    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    cur = vcam.objc_msgSend(shared, "audioMuted")
    nxt = not cur
    vcam.objc_msgSend(shared, "setAudioMuted:", nxt)

    if vcam.objc_msgSend(shared, "isPlayerSource"):
        player = vcam.objc_msgSend(shared, "valueForKey:", vcam.PLAYER_KEY)
        if player is not None:
            muted = vcam.objc_msgSend(player, "audioMuted")
            vcam.objc_msgSend(player, "setAudioMuted:", not muted)

    vcam.objc_msgSend(self_, "_0xA14d5E7F")
    return nxt


def audio_inject_tapped(vcam, self_):
    if not vcam.objc_msgSend(vcam.CLASS_A3F9C1E2,
                             "_0x9D4e6F2B:", vcam.FEATURE_AUDIO_INJECT):
        vcam.objc_msgSend(self_, "showFeatureDisabledTip")
        return False
    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    cur = vcam.objc_msgSend(shared, "audioInjectEnabled")
    vcam.objc_msgSend(shared, "setAudioInjectEnabled:", not cur)
    now = vcam.objc_msgSend(shared, "audioInjectEnabled")

    if now:
        muted = vcam.objc_msgSend(shared, "audioMuted")
        vcam.objc_msgSend(shared, "setAudioMuted:", not muted)

    if vcam.objc_msgSend(shared, "isPlayerSource"):
        player = vcam.objc_msgSend(shared, "valueForKey:", vcam.PLAYER_KEY)
        if player is not None:
            vcam.objc_msgSend(player, "setAudioMuted:",
                              not vcam.objc_msgSend(player, "audioMuted"))

    vcam.objc_msgSend(self_, "_0xA14d5E7F")
    return now


def rotate_tapped(vcam, self_):
    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    deg = vcam.objc_msgSend(shared, "rotationDegree")
    nxt = vcam.next_rotation_degree(deg)
    vcam.objc_msgSend(shared, "setRotationDegree:", nxt)
    vcam.objc_msgSend(self_, "_0xA14d5E7F")
    return nxt


def disable_tapped(vcam, self_):
    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    vcam.objc_msgSend(shared, "_0x2B4c6D8F")
    vcam.objc_msgSend(self_, "toggleMenu")


# ---------------------------------------------------------------------------
# 手势与浮层
# ---------------------------------------------------------------------------
def _0x4F7a1B3E(vcam, self_, recognizer):
    st = vcam.objc_msgSend(recognizer, "state")
    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    logging = vcam.objc_msgSend(shared, "loggingEnabled")
    vcam.objc_msgSend(shared, "setLoggingEnabled:", not logging)

    ud = vcam.objc_msgSend(vcam.CLASS_NSUSERDEFAULTS, "standardUserDefaults")
    vcam.objc_msgSend(ud, "setBool:forKey:", not logging, vcam.LOGGING_KEY)
    vcam.objc_msgSend(ud, "synchronize")

    return vcam.objc_msgSend(self_, "_0x5A8b2C4F:", st)


def _0x5A8b2C4F(vcam, self_, state):
    screen = vcam.objc_msgSend(vcam.CLASS_UISCREEN, "mainScreen")
    bounds = vcam.objc_msgSend(screen, "bounds")
    win = vcam.alloc_init(vcam.self_class)
    vcam.objc_msgSend(win, "setWindowLevel:", vcam.UIWindowLevelAlert)

    black = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "blackColor")
    dim = vcam.objc_msgSend(black, "colorWithAlphaComponent:", 0.5)
    vcam.objc_msgSend(win, "setBackgroundColor:", dim)

    lay = vcam.objc_msgSend(win, "layer")
    vcam.objc_msgSend(lay, "setCornerRadius:", 0.0)
    vcam.objc_msgSend(lay, "setClipsToBounds:", True)
    vcam.objc_msgSend(win, "setTag:", MENU_TAG)

    vc = vcam.alloc_init(vcam.CLASS_UIVIEWCONTROLLER)
    vcam.objc_msgSend(vc, "setRootViewController:", win)

    lbl = vcam.alloc_init(vcam.CLASS_UILABEL)
    vcam.objc_msgSend(lbl, "initWithFrame:", vcam.CENTERED_RECT)
    vcam.objc_msgSend(lbl, "setText:", vcam._deobf_string(0x297614))

    green = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "greenColor")
    red   = vcam.objc_msgSend(vcam.CLASS_UICOLOR, "redColor")
    vcam.objc_msgSend(lbl, "setTextColor:",
                      green if state == vcam.UIGestureRecognizerStateBegan else red)

    font = vcam.objc_msgSend(vcam.CLASS_UIFONT, "boldSystemFontOfSize:", 20)
    vcam.objc_msgSend(lbl, "setFont:", font)
    vcam.objc_msgSend(lbl, "setTextAlignment:", 1)

    root = vcam.objc_msgSend(vc, "view")
    vcam.objc_msgSend(root, "addSubview:", lbl)

    hide = state != vcam.UIGestureRecognizerStateBegan
    vcam.objc_msgSend(win, "setHidden:", hide)
    vcam.objc_msgSend(win, "setAlpha:", ALPHA_BY_CALLSITE[0x297e74])
    vcam.objc_msgSend(vcam.CLASS_UIVIEW,
                      "animateWithDuration:animations:completion:",
                      0.25, lambda: None, None)
    return win


def handle_long_press(vcam, self_, recognizer):
    pt = vcam.objc_msgSend(recognizer, "locationInView:", vcam.self)
    st = vcam.objc_msgSend(recognizer, "state")
    _  = vcam.objc_msgSend(vcam.self, "frame")
    btn = vcam.objc_msgSend(vcam.self, "button")

    if st == vcam.UIGestureRecognizerStateBegan:
        vcam.objc_msgSend(btn, "setAlpha:", ALPHA_BY_CALLSITE[0x29a960])
        screen = vcam.objc_msgSend(vcam.CLASS_UISCREEN, "mainScreen")
        vcam.objc_msgSend(btn, "setFrame:", vcam.objc_msgSend(screen, "bounds"))
        vcam.objc_msgSend(btn, "setAlpha:", ALPHA_BY_CALLSITE[0x29ac2c])


def show_feature_disabled_tip(vcam, self_):
    top = vcam.objc_msgSend(self_, "topViewController")
    if top is None:
        return None
    title = vcam._deobf_string(0x3f6828)
    msg   = vcam._deobf_string(0x3f68a8)
    alert = vcam.objc_msgSend(vcam.CLASS_UIALERTCONTROLLER,
                              "alertControllerWithTitle:message:preferredStyle:",
                              title, msg, vcam.UIAlertControllerStyleAlert)
    vcam.objc_msgSend(top, "presentViewController:animated:completion:",
                      alert, True, None)
    return alert


def top_view_controller(vcam, self_):
    app = vcam.objc_msgSend(vcam.CLASS_UIAPPLICATION, "sharedApplication")

    scenes = vcam.objc_msgSend(app, "connectedScenes")
    for sc in vcam._enumerate(scenes):
        act = vcam.objc_msgSend(sc, "activationState")
        if act != vcam.UISceneActivationStateForegroundActive:
            continue
        for w in vcam._enumerate(vcam.objc_msgSend(sc, "windows")):
            if vcam.objc_msgSend(w, "isKeyWindow"):
                vc = vcam.objc_msgSend(w, "rootViewController")
                if vc is not None:
                    return _presented_chain(vcam, vc)

    for w in vcam._enumerate(vcam.objc_msgSend(app, "windows")):
        if vcam.objc_msgSend(w, "isHidden"):
            continue
        vc = vcam.objc_msgSend(w, "rootViewController")
        if vc is not None:
            return _presented_chain(vcam, vc)
    return None


def _presented_chain(vcam, vc):
    top = vcam.objc_msgSend(vc, "presentedViewController")
    while top is not None:
        vc = top
        top = vcam.objc_msgSend(vc, "presentedViewController")
    return vc


# ---------------------------------------------------------------------------
# 相册选片
# ---------------------------------------------------------------------------
def select_from_photo_library(vcam, self_):
    if vcam._os_at_least(14):
        cfg = vcam.alloc_init(vcam.CLASS_PHPICKERCONFIGURATION)
        flt = vcam.objc_msgSend(vcam.CLASS_PHPICKERFILTER, "videosFilter")
        vcam.objc_msgSend(cfg, "setFilter:", flt)
        vcam.objc_msgSend(cfg, "setSelectionLimit:", 1)

        pc = vcam.alloc_init(vcam.CLASS_PHPICKERVIEWCONTROLLER)
        vcam.objc_msgSend(pc, "initWithConfiguration:", cfg)
        vcam.objc_msgSend(pc, "setDelegate:", self_)
        top = vcam.objc_msgSend(self_, "topViewController")
        vcam.objc_msgSend(top, "presentViewController:animated:completion:",
                          pc, True, None)
        return pc

    pc = vcam.alloc_init(vcam.CLASS_UIIMAGEPICKERCONTROLLER)
    vcam.objc_msgSend(pc, "setSourceType:", 0)
    media = vcam.objc_msgSend(vcam.CLASS_NSARRAY, "arrayWithObjects:count:",
                              (vcam.CLASS_UTTYPE_MOVIE,), 1)
    vcam.objc_msgSend(pc, "setMediaTypes:", media)
    vcam.objc_msgSend(pc, "setVideoQuality:", 0)
    vcam.objc_msgSend(pc, "setVideoExportPreset:", vcam.AVAssetExportPresetHighestQuality)

    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    vcam.objc_msgSend(pc, "setDelegate:", self_)
    top = vcam.objc_msgSend(self_, "topViewController")
    vcam.objc_msgSend(top, "presentViewController:animated:completion:",
                      pc, True, None)
    _ = shared
    return pc


def picker_did_finish_picking(vcam, self_, picker, results):
    vcam.objc_msgSend(picker, "dismissViewControllerAnimated:completion:",
                      True, None)
    item = vcam.objc_msgSend(results, "firstObject")
    if item is None:
        return None
    provider = vcam.objc_msgSend(item, "itemProvider")
    vcam.objc_msgSend(
        provider, "loadFileRepresentationForTypeIdentifier:completionHandler:",
        vcam.UTTYPE_MOVIE_IDENTIFIER,
        lambda url, err: vcam.objc_msgSend(self_, "_0x9C2d4E7A:", url, err))
    return provider


def _0x9C2d4E7A(vcam, self_, url, error):
    file_url = vcam.objc_msgSend(vcam.CLASS_NSURL, "fileURLWithPath:",
                                 vcam._path_of(url))
    asset = vcam.objc_msgSend(vcam.CLASS_AVASSET, "assetWithURL:", file_url)
    tracks = vcam.objc_msgSend(asset, "tracksWithMediaType:", vcam.AVMediaTypeVideo)
    track = vcam.objc_msgSend(tracks, "firstObject")

    size  = vcam.objc_msgSend(track, "naturalSize")
    xform = vcam.objc_msgSend(track, "preferredTransform")
    dur   = vcam.objc_msgSend(track, "duration")
    fps   = vcam.objc_msgSend(track, "nominalFrameRate")

    info = vcam.objc_msgSend(vcam.CLASS_NSSTRING, "stringWithFormat:",
                             vcam.VIDEO_INFO_FORMAT, size, dur, fps, xform)
    shared = vcam.objc_msgSend(vcam.CLASS_A3F9C1E2, "shared")
    vcam.objc_msgSend(shared, "setCurrentVideoInfo:", info)
    return info


# ---------------------------------------------------------------------------
# UIWindow 协议与访问器
# ---------------------------------------------------------------------------
def can_become_key_window(vcam, self_):
    return True


def show(vcam, self_):
    vcam.objc_msgSend(self_, "setHidden:", False)


def hide(vcam, self_):
    vcam.objc_msgSend(self_, "setHidden:", True)


def dealloc(vcam, self_):
    timer = vcam._ivar_status_timer(self_)
    if timer is not None:
        vcam.objc_msgSend(timer, "invalidate")
    return vcam.objc_msgSendSuper2(self_, "dealloc")


ACCESSORS = (
    ("button",        "setButton:",        0x29ae8c, 0x29aef8),
    ("menuWindow",    "setMenuWindow:",    0x29af68, 0x29afd4),
    ("menuView",      "setMenuView:",      0x29b044, 0x29b0b0),
    ("isMenuVisible", "setIsMenuVisible:", 0x29b120, 0x29b194),
    ("statusTimer",   "setStatusTimer:",   0x29b20c, 0x29b278),
)


def make_accessors(vcam):
    out = {}
    for name, setter, gaddr, saddr in ACCESSORS:
        out[name]   = _make_accessor(vcam, name, setter, gaddr)
        out[setter] = _make_setter(vcam, name, saddr)
    return out


def _make_accessor(vcam, name, setter, addr):
    def f(self_):
        return vcam.ivar_get(self_, name)
    f.__name__ = name
    f.addr = addr
    return f


def _make_setter(vcam, name, addr):
    def f(self_, value):
        return vcam.ivar_set(self_, name, value)
    f.__name__ = f"set{name[0].upper()}{name[1:]}:"
    f.addr = addr
    return f


def cxx_destruct(vcam, self_):
    raise NotImplementedError("ARC ivar 释放序列，无外部调用")
