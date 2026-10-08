# -*- coding: utf-8 -*-
"""
video_inject.py — VCam 视频注入链。

覆盖四段链路：
    1) 8 个 swizzle 安装器（UI 层 + AVCaptureSession + 图层 + delegate）
    2) doPlayWithURL:isLocal:      播放入口
    3) _0x2E6a8D4F:                帧泵（显示链接驱动）
    4) processVideoBuffer:         CIImage 像素管线
        _0x7D9e2F4A:_0x8E1f3A5B:  样本构造（PTS 重打）
"""

from __future__ import annotations

MENU_TAG              = 1447248205
MENU_ALPHA_CONST      = 0.85
MENU_ALPHA_CONST_ADDR = 0x34B728
LONG_PRESS_MIN        = 0.2
LONG_PRESS_MIN_ADDR   = 0x34B720
LONG_PRESS_MENU       = 1.5

CORNER_RADIUS_BY_CALLSITE = {
    0x27edb4: 12.0,
    0x289344: 15.0,
    0x28c76c: 8.0,
    0x28c9f0: 8.0,
    0x28dd78: 8.0,
    0x297b10: 8.0,
    0x2a7d28: 10.0,
}

ALPHA_BY_CALLSITE = {
    0x28fde4: 0.0, 0x28ffe4: 1.0, 0x290074: 0.0,
    0x297e74: 0.0, 0x298058: 1.0, 0x298328: 0.0,
    0x29a960: 0.5, 0x29ac2c: 1.0,
    0x2a7d64: 0.0, 0x2a8478: 1.0, 0x2a8748: 0.0,
}

TIMER_INTERVAL = 0.5

CV_PIXEL_BUFFER_WIDTH_KEY           = "kCVPixelBufferWidthKey"
CV_PIXEL_BUFFER_HEIGHT_KEY          = "kCVPixelBufferHeightKey"
CV_PIXEL_BUFFER_PIXEL_FORMAT_KEY    = "kCVPixelBufferPixelFormatTypeKey"
CV_PIXEL_BUFFER_IO_SURFACE_PROPS_KEY = "kCVPixelBufferIOSurfacePropertiesKey"


# ---------------------------------------------------------------------------
# swizzle 层
# ---------------------------------------------------------------------------
SWAP_PAIRS = (
    ("windows",       "vcam_windows"),
    ("keyWindow",     "vcam_keyWindow"),
    ("windows",       "vcam_sceneWindows"),
    ("keyWindow",     "vcam_sceneKeyWindow"),
    ("canBecomeKeyWindow", "vcam_canBecomeKeyWindow"),
    ("startRunning",  "vcam_startRunning"),
    ("stopRunning",   "vcam_stopRunning"),
    ("addInput:",     "vcam_addInput:"),
    ("addSublayer:",  "vcam_addSublayer:"),
    ("setSession:",   "vcam_setSession:"),
    ("setSampleBufferDelegate:queue:", "vcam_setSampleBufferDelegate:queue:"),
    ("setSampleBufferDelegate:queue:", "vcam_setAudioSampleBufferDelegate:queue:"),
)


def _template_swizzle(vcam, obj, orig_sel, alias_sel,
                      add_addr, repl_addr, exch_addr):
    """四步模板：取 Method → 补桩 → replace → exchange。"""
    cls = vcam.objc_msgSend(obj, "class")
    m_orig  = vcam.class_getInstanceMethod(cls, orig_sel)
    m_alias = vcam.class_getInstanceMethod(cls, alias_sel)

    vcam.objc_msgSend(obj, orig_sel)

    if m_alias is None:
        cls = vcam.objc_msgSend(obj, "class")
        imp   = vcam.method_getImplementation(m_orig)
        types = vcam.method_getTypeEncoding(m_orig)
        vcam.class_addMethod(cls, alias_sel, imp, types)

    cls = vcam.objc_msgSend(obj, "class")
    m_alias = vcam.class_getInstanceMethod(cls, alias_sel)
    new_imp   = vcam.method_getImplementation(m_alias)
    new_types = vcam.method_getTypeEncoding(m_alias)
    vcam.class_replaceMethod(cls, orig_sel, new_imp, new_types)
    vcam.method_exchangeImplementations(m_orig, m_alias)


def swap_windows(vcam, obj):
    _template_swizzle(vcam, obj, "windows", "vcam_windows",
                      0x284b20, 0x284b84, 0x284b94)


def swap_key_window(vcam, obj):
    _template_swizzle(vcam, obj, "keyWindow", "vcam_keyWindow",
                      0x284c64, 0x284cc8, 0x284cd8)


def swap_scene_windows(vcam, obj):
    _template_swizzle(vcam, obj, "windows", "vcam_sceneWindows",
                      0x2852c0, 0x285324, 0x285334)


def swap_scene_key_window(vcam, obj, min_version):
    info = vcam.objc_msgSend(vcam.NSProcessInfo, "processInfo")
    info = vcam.objc_retainAutoreleasedReturnValue(info)
    ok = vcam.objc_msgSend(info, "isOperatingSystemAtLeastVersion:", min_version)
    vcam.objc_release(info)
    if not ok:
        return False
    _template_swizzle(vcam, obj, "keyWindow", "vcam_sceneKeyWindow",
                      0x2854a0, 0x285504, 0x285514)
    return True


def swap_can_become_key_window(vcam, obj):
    _template_swizzle(vcam, obj, "canBecomeKeyWindow", "vcam_canBecomeKeyWindow",
                      0x286064, 0x2860d4, 0x2860ec)


def swap_capture_session(vcam, session):
    _template_swizzle(vcam, session, "startRunning", "vcam_startRunning",
                      0x2864bc, 0x286520, 0x286530)
    _template_swizzle(vcam, session, "stopRunning", "vcam_stopRunning",
                      0x286600, 0x286664, 0x286674)
    _template_swizzle(vcam, session, "addInput:", "vcam_addInput:",
                      0x286744, 0x2867a8, 0x2867b8)


def swap_layer_session(vcam, layer):
    _template_swizzle(vcam, layer, "addSublayer:", "vcam_addSublayer:",
                      0x286e70, 0x286ed4, 0x286ee4)
    _template_swizzle(vcam, layer, "setSession:", "vcam_setSession:",
                      0x286fb4, 0x287018, 0x287028)


def swap_video_sample_buffer_delegate(vcam, output):
    _template_swizzle(vcam, output,
                      "setSampleBufferDelegate:queue:",
                      "vcam_setSampleBufferDelegate:queue:",
                      0x2879d8, 0x287a3c, 0x287a4c)


def replace_instance_method(vcam, cls, selector, new_imp):
    m        = vcam.class_getInstanceMethod(cls, selector)
    types    = vcam.method_getTypeEncoding(m)
    old_imp  = vcam.method_getImplementation(m)
    vcam.class_replaceMethod(cls, selector, new_imp, types)
    return old_imp


def install_video_hooks_once(vcam, dispatch_once, token):
    already = False
    if already:
        return False
    dispatch_once(token, lambda: None)
    return True


def alloc_format_struct():
    raise NotImplementedError(
        "需要 vcam.calloc 句柄；结构布局见 0x2a9adc..0x2a9af4")


def setup_format_descriptor(vcam, factory):
    return factory()


# ---------------------------------------------------------------------------
# 播放入口
# ---------------------------------------------------------------------------
def do_play_with_url(vcam, self_, url, is_local,
                     install_video, install_unknown2, install_audio,
                     show_preview):
    player = vcam.objc_alloc_init(vcam.CLASS_VCAM_FFPLAYER)
    vcam.objc_msgSend(player, "setDelegate:", self_)
    vcam.objc_msgSend(player, "setLoopEnabled:", True)
    vcam.objc_msgSend(player, "setAudioMuted:", False)

    vcam.__common_is_local = bool(is_local)

    install_video()
    alloc_format_struct()
    setup_format_descriptor(vcam, install_unknown2)
    install_audio()

    vcam.objc_msgSend(self_, "showNetworkPreviewWindow")

    queue = vcam.dispatch_get_global_queue(0, 0)
    vcam.dispatch_async(queue, lambda: None)
    return player


# ---------------------------------------------------------------------------
# 帧泵
# ---------------------------------------------------------------------------
def frame_pump(vcam, self_, ctx):
    link = vcam._get_0x1F9b3A5C(self_)

    if vcam._is_link_running(link):
        vcam.objc_msgSend(link, "invalidate")

    if not vcam._0x6C8d1E3F(self_):
        pass
    else:
        layer_a = vcam._0x4C6a8D1F(self_)
        if vcam._layer_opacity(layer_a) == 0:
            vcam.objc_msgSend(layer_a, "setOpacity:", 1.0)

        layer_b = vcam._0x9D3f7B2E(self_)
        if vcam._layer_opacity(layer_b) == 0:
            vcam.objc_msgSend(layer_b, "setOpacity:", 1.0)

        cur_gravity = vcam.objc_msgSend(layer_a, "videoGravity")
        want_gravity = ctx.gravity_string
        if not vcam.objc_msgSend(cur_gravity, "isEqualToString:", want_gravity):
            vcam.objc_msgSend(layer_a, "setVideoGravity:", want_gravity)

        for lyr in (layer_a, layer_b):
            if vcam._layer_opacity(lyr) == 0:
                vcam.objc_msgSend(lyr, "setOpacity:", 1.0)

    if vcam._0x7A1c3E9D(self_):
        want = vcam.objc_msgSend(layer_b, "bounds")
        have = vcam.objc_msgSend(layer_b, "frame")
        if not vcam.CGRectEqualToRect(want, have):
            vcam.objc_msgSend(layer_b, "setFrame:", want)

    mode = vcam._0x2B4d6F8A(self_)
    if mode == 1:
        t = vcam.CATransform3DMakeRotation(ctx.deg1_rad)
        vcam.objc_msgSend(layer_b, "setTransform:", t)
    elif mode == 2:
        t = vcam.CATransform3DMakeRotation(ctx.deg2_rad)
        vcam.objc_msgSend(layer_b, "setTransform:", t)
    else:
        t = vcam.CATransform3DIdentity()
        vcam.objc_msgSend(layer_b, "setTransform:", t)

    now = vcam.CACurrentMediaTime()
    if not vcam._0x5E8a1C3D(self_, now):
        return None

    if not vcam.objc_msgSend(layer_b, "isReadyForMoreMediaData"):
        return None

    vcam.__bss_dropped_frames += 1
    vcam.objc_msgSend(self_, "set_0x2B4d6F8A:", mode)

    buf = build_sample_buffer(vcam, ctx)
    vcam.objc_msgSend(layer_b, "flush")

    cached = ctx.cached_sample_buffer
    if cached is None:
        vcam.CFRelease(cached)
        vcam.objc_msgSend(self_, "set_0x8E2d4F6A:", None)
        copy = vcam.CMSampleBufferCreateCopy(vcam.kCFAllocatorDefault,
                                             buf, vcam.__const_universe)
        ctx.cached_sample_buffer = copy

    vcam.objc_msgSend(layer_b, "enqueueSampleBuffer:", ctx.cached_sample_buffer)
    return ctx.cached_sample_buffer


# ---------------------------------------------------------------------------
# 样本构造
# ---------------------------------------------------------------------------
def build_sample_buffer(vcam, ctx):
    src = ctx.cached_sample_buffer
    if src is None:
        return None

    fmt   = vcam.CMSampleBufferGetFormatDescription(src)
    media = vcam.CMFormatDescriptionGetMediaType(fmt)
    if not vcam._media_type_is_video(media):
        return None
    if not vcam._0x6C8d1E3F(ctx.owner):
        return None

    vcam.dispatch_sync(ctx.frame_queue, lambda: None)
    vcam.objc_msgSend(ctx.lock, "lock")
    src = vcam.CFRelease(src)
    vcam.objc_msgSend(ctx.lock, "unlock")

    if not vcam.CMSampleBufferIsValid(src):
        return None

    timing  = vcam.CMSampleBufferGetSampleTimingInfo(src)
    old_pts = vcam.CMTimeGetSeconds(timing.presentation_time_stamp)

    now   = vcam.CACurrentMediaTime()
    delta = vcam.CMTimeAdd(timing.duration, vcam.CMTimeMake(0, 0))
    pts   = vcam.CMTimeMake(int(now), int(old_pts * 1e9))
    _     = delta

    pix = vcam.CMSampleBufferGetImageBuffer(src)
    w   = vcam.CVPixelBufferGetWidth(pix)
    h   = vcam.CVPixelBufferGetHeight(pix)

    vcam.CFRetain(pix)
    fmt2 = vcam.CMVideoFormatDescriptionCreateForImageBuffer(None, pix)
    vcam.CVPixelBufferRelease(pix)

    out = vcam._0x2794EC(vcam, w, h)

    new_buf = vcam.CMSampleBufferCreateReadyWithImageBuffer(
        vcam.kCFAllocatorDefault, fmt2, pix, pts, timing.duration)

    if vcam.CMSampleBufferIsValid(new_buf):
        att = vcam.CMCopyDictionaryOfAttachments(new_buf, True)
        vcam.CMSetAttachments(new_buf, att, True)

    vcam.objc_msgSend(ctx.lock, "lock")
    ctx.last_sample_buffer = new_buf
    vcam.objc_msgSend(ctx.lock, "unlock")
    return new_buf


def _0x2794EC(vcam, w, h):
    raise NotImplementedError("需要 0x2794ec 的原始算术；无外部调用可参照")


# ---------------------------------------------------------------------------
# 像素管线
# ---------------------------------------------------------------------------
def process_video_buffer(vcam, self_, cvbuffer, ctx):
    w = vcam.CVPixelBufferGetWidth(cvbuffer)
    h = vcam.CVPixelBufferGetHeight(cvbuffer)

    image = vcam.objc_msgSend(vcam.CLASS_CIIMAGE,
                              "imageWithCVPixelBuffer:", cvbuffer)

    if vcam.objc_msgSend(ctx.mode_string, "isEqualToString:",
                         ctx.mirror_mode_name):
        s = vcam.CGAffineTransformMakeScale(-1.0, 1.0)
        s = vcam.CGAffineTransformMakeTranslation(s, float(w), 0.0)
        image = vcam.objc_msgSend(image, "imageByApplyingTransform:", s)

    image = vcam.objc_msgSend(image, "imageByApplyingCGOrientation:",
                              ctx.cg_orientation)

    if ctx.rotation_deg != 0:
        r = vcam.CGAffineTransformMakeRotation(ctx.rotation_rad)
        image = vcam.objc_msgSend(image, "imageByApplyingTransform:", r)

        ext = vcam.objc_msgSend(image, "extent")
        tx = -(ext.origin_x + ext.size_width / 2.0)
        ty = -(ext.origin_y + ext.size_height / 2.0)
        t  = vcam.CGAffineTransformMakeTranslation(tx, ty)
        image = vcam.objc_msgSend(image, "imageByApplyingTransform:", t)

    sc = vcam.CGAffineTransformMakeScale(ctx.scale_x, ctx.scale_y)
    image = vcam.objc_msgSend(image, "imageByApplyingTransform:", sc)

    vcam.CVPixelBufferPoolRelease(ctx.pool)
    attrs = vcam.objc_msgSend(
        vcam.CLASS_NSDICTIONARY, "dictionaryWithObjects:forKeys:count:",
        (vcam.numberWithUnsignedLong_(w),
         vcam.numberWithUnsignedInt_(h),
         vcam.numberWithUnsignedInt_(ctx.pixel_format),
         vcam.CLASS_NSDICTIONARY),
        (CV_PIXEL_BUFFER_WIDTH_KEY,
         CV_PIXEL_BUFFER_HEIGHT_KEY,
         CV_PIXEL_BUFFER_PIXEL_FORMAT_KEY,
         CV_PIXEL_BUFFER_IO_SURFACE_PROPS_KEY),
        4)
    ctx.pool = vcam.CVPixelBufferPoolCreate(None, attrs)

    out = vcam.CVPixelBufferPoolCreatePixelBuffer(None, ctx.pool, None)
    if not out:
        out = vcam.CVPixelBufferCreate(
            None, w, h, ctx.pixel_format,
            (cvbuffer, True, None, None))

    vcam.dispatch_sync(ctx.ci_queue, lambda: vcam._render(ctx, image, out))

    if not vcam.objc_msgSend(ctx.preview_layer, "isHidden"):
        ci = vcam.objc_msgSend(vcam.CLASS_CIIMAGE,
                               "imageWithCVPixelBuffer:", out)
        ui = vcam.objc_msgSend(vcam.CLASS_UIIMAGE, "imageWithCIImage:", ci)
        vcam.dispatch_async(vcam.__dispatch_main_q,
                            lambda: vcam._set_preview(ctx, ui))
    return out


# ---------------------------------------------------------------------------
# delegate 回调与辅助
# ---------------------------------------------------------------------------
def ffplayer_did_output_video_buffer(vcam, self_, player, buffer, pts):
    pool = vcam.objc_autoreleasePoolPush()
    vcam.objc_storeStrong(self_, "_0x5E8a1C3D", pts)
    vcam.objc_msgSend(self_, "processVideoBuffer:", buffer)
    vcam.objc_autoreleasePoolPop(pool)
    return None


def ffplayer_video_size_changed(vcam, self_, player, size):
    raise NotImplementedError("见 entry 0x27bf08；本轮未展开")


def release_pixel_buffer_pool(vcam, pool):
    raise NotImplementedError("见 entry 0x2805a4；本轮未展开")


def _0x6C8d1E3F(vcam, self_):
    raise NotImplementedError("纯 ivar getter；需 ldr 立即数定位偏移")
