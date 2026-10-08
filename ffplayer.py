# -*- coding: utf-8 -*-
"""
ffplayer.py — VCamFFPlayer：FFmpeg + AVFoundation 解码播放核心。

覆盖生命周期、openURL、传输控制、解码器装配、读帧主循环、
音视频帧处理、像素缓冲转换、重开流、资源清理、状态与错误上报、
以及全部 ivar 直读写访问器。
"""

from __future__ import annotations

PIXEL_FORMAT_KEYS = (
    "kCVPixelBufferPixelFormatTypeKey",
    "kCVPixelBufferWidthKey",
    "kCVPixelBufferHeightKey",
    "kCVPixelBufferIOSurfacePropertiesKey",
)


class _State:
    IDLE    = "idle"
    OPENING = "opening"
    PLAYING = "playing"
    PAUSED  = "paused"
    STOPPED = "stopped"
    ERROR   = "error"


# ---------------------------------------------------------------------------
# 生命周期
# ---------------------------------------------------------------------------
def init(vcam, self_):
    self_ = vcam.objc_msgSendSuper2(self_, "init")
    vcam.zero_ffmpeg_context(self_)
    return self_


def dealloc(vcam, self_):
    vcam.objc_msgSend(self_, "cleanupFFmpeg")
    return vcam.objc_msgSendSuper2(self_, "dealloc")


# ---------------------------------------------------------------------------
# openURL
# ---------------------------------------------------------------------------
def open_url(vcam, self_, url):
    s = vcam.objc_msgSend(url, "length")
    vcam.objc_msgSend(self_, "updateState:", _State.OPENING)

    if s == 0:
        msg = vcam.objc_msgSend(vcam.CLASS_NSSTRING, "stringWithFormat:",
                                "请输入有效的 URL")
        vcam.objc_msgSend(self_, "reportError:", msg)
        return False

    text = vcam.objc_msgSend(url, "UTF8String")

    p1 = vcam.objc_msgSend(url, "hasPrefix:", vcam.SCHEME_LOCAL)
    p2 = vcam.objc_msgSend(url, "hasPrefix:", vcam.SCHEME_NET)
    if p1 == p2:
        msg = vcam.objc_msgSend(vcam.CLASS_NSSTRING, "stringWithFormat:",
                                "拉流地址验证失败，禁止播放放", text)
        vcam.objc_msgSend(self_, "reportError:", msg)
        vcam.objc_msgSend(self_, "cleanupFFmpeg")
        return False

    live = vcam.objc_msgSend(url, "containsString:", "rtsp", "rtmp")
    vcam.objc_msgSend(self_, "setIsLiveStream:", bool(live))

    vcam.objc_msgSend(self_, "cleanupFFmpeg")
    vcam.objc_msgSend(self_, "setupVideoDecoder")
    vcam.objc_msgSend(self_, "setupAudioDecoder")
    vcam.objc_msgSend(self_, "updateState:", _State.PLAYING)
    return True


# ---------------------------------------------------------------------------
# 传输控制
# ---------------------------------------------------------------------------
def play(vcam, self_):
    vcam.objc_msgSend(self_, "updateState:", _State.PLAYING)


def pause(vcam, self_):
    vcam.objc_msgSend(self_, "updateState:", _State.PAUSED)


def stop(vcam, self_):
    vcam.objc_msgSend(self_, "updateState:", _State.STOPPED)


def seek_to_time(vcam, self_, seconds):
    ts = vcam.av_time_base(seconds)
    vcam.av_seek_frame(self_.fmt_ctx, -1, ts, vcam.SEEK_BACKWARD)
    vcam.avcodec_flush_buffers(self_.video_codec_ctx)
    vcam.avcodec_flush_buffers(self_.audio_codec_ctx)


# ---------------------------------------------------------------------------
# 解码器装配
# ---------------------------------------------------------------------------
def setup_video_decoder(vcam, self_):
    dec = vcam.avcodec_find_decoder(self_.video_codec_id)
    if dec is None:
        return False
    ctx = vcam.avcodec_alloc_context3(dec)
    if ctx is None:
        return False

    ret = vcam.avcodec_parameters_to_context(ctx, self_.video_par)
    if ret < 0:
        vcam.avcodec_free_context(ctx)
        vcam._0x2f01cc(self_, ret)
        return False

    vcam.av_hwdevice_ctx_create(self_.hw_device_ref,
                                vcam.HW_DEVICE_TYPE, vcam.HW_DEVICE_NAME)
    vcam.av_buffer_ref(self_.hw_device_ref)

    ret = vcam.avcodec_open2(ctx, dec, self_.codec_opts)
    if ret < 0:
        vcam.avcodec_free_context(ctx)
        vcam._0x2f01cc(self_, ret)
        return False

    self_.video_codec_ctx = ctx
    vcam.objc_msgSend(self_, "setHasVideo:", True)
    return True


def setup_audio_decoder(vcam, self_):
    dec = vcam.avcodec_find_decoder(self_.audio_codec_id)
    if dec is None:
        vcam.objc_msgSend(self_, "setHasAudio:", False)
        return False

    ctx = vcam.avcodec_alloc_context3(dec)
    vcam.avcodec_parameters_to_context(ctx, self_.audio_par)
    ret = vcam.avcodec_open2(ctx, dec, self_.codec_opts)
    if ret < 0:
        vcam.avcodec_free_context(ctx)
        vcam.objc_msgSend(self_, "setHasAudio:", False)
        return False
    self_.audio_codec_ctx = ctx

    vcam.av_channel_layout_default(self_.swr_in_layout)
    ret = vcam.swr_alloc_set_opts2(self_.swr,
                                   self_.swr_in_layout, self_.swr_in_format,
                                   self_.swr_in_rate,
                                   self_.swr_out_layout, self_.swr_out_format,
                                   self_.swr_out_rate,
                                   0, None)
    if ret < 0 or vcam.swr_init(self_.swr) < 0:
        vcam.swr_free(self_.swr)
        vcam.objc_msgSend(self_, "setHasAudio:", False)
        return False

    vcam.objc_msgSend(self_, "setHasAudio:", True)
    return True


# ---------------------------------------------------------------------------
# 读帧主循环
# ---------------------------------------------------------------------------
def read_loop(vcam, self_):
    pkt   = vcam.av_packet_alloc()
    frame = vcam.av_frame_alloc()

    while not vcam._ivar_stopped(self_):
        vcam.usleep(vcam.READ_INTERVAL_US)

        ret = vcam.av_read_frame(self_.fmt_ctx, pkt)
        if ret < 0:
            if vcam.objc_msgSend(self_, "isLiveStream"):
                vcam.usleep(vcam.RECONNECT_BACKOFF_US)
                vcam.av_seek_frame(self_.fmt_ctx, -1, 0, vcam.SEEK_BACKWARD)
                vcam.avcodec_flush_buffers(self_.video_codec_ctx)
                vcam.avcodec_flush_buffers(self_.audio_codec_ctx)
                vcam._0x2aa134(self_)
                vcam.usleep(vcam.RECONNECT_BACKOFF_US)
                continue
            err = vcam.av_strerror(ret, vcam.err_buf, 64)
            vcam.objc_msgSend(self_, "reportError:", err)
            break

        if pkt.stream_index == self_.video_stream_index:
            vcam.avcodec_send_packet(self_.video_codec_ctx, pkt)
            vcam.avcodec_receive_frame(self_.video_codec_ctx, frame)
            vcam.objc_msgSend(self_, "handleVideoFrame:", frame)
            vcam.av_frame_unref(frame)
        else:
            vcam.avcodec_send_packet(self_.audio_codec_ctx, pkt)
            vcam.avcodec_receive_frame(self_.audio_codec_ctx, frame)
            vcam.objc_msgSend(self_, "handleAudioFrame:", frame)
            vcam.av_frame_unref(frame)

        vcam.av_packet_unref(pkt)

    vcam.av_frame_free(frame)
    vcam.av_packet_free(pkt)


def handle_video_frame(vcam, self_, frame):
    cvbuf = vcam.objc_msgSend(self_, "convertFrameToPixelBuffer:", frame)
    size  = vcam._pixel_buffer_size(cvbuf)

    if size != vcam._ivar_video_size(self_):
        vcam.objc_msgSend(self_, "setVideoSize:", size)
        d = vcam.objc_msgSend(self_, "delegate")
        if d is not None:
            vcam.objc_msgSend(d, "ffplayer:videoSizeChanged:", self_, size)

    pts = vcam._frame_pts(frame)
    d = vcam.objc_msgSend(self_, "delegate")
    if vcam.objc_msgSend(d, "respondsToSelector:",
                         "ffplayer:didOutputVideoBuffer:pts:"):
        vcam.objc_msgSend(d, "ffplayer:didOutputVideoBuffer:pts:",
                          self_, cvbuf, pts)
    return cvbuf


def handle_audio_frame(vcam, self_, frame):
    pcm, nframes = vcam._resample_audio(self_.swr, frame)
    pts = vcam._frame_pts(frame)
    d = vcam.objc_msgSend(self_, "delegate")
    return vcam.objc_msgSend(d, "ffplayer:didOutputAudioData:frames:pts:",
                             self_, pcm, nframes, pts)


def convert_frame_to_pixel_buffer(vcam, self_, frame):
    vcam.CVPixelBufferPoolRelease(self_.pool)

    attrs = vcam._pool_attributes(self_.out_w, self_.out_h, self_.out_pix_fmt)
    self_.pool = vcam.CVPixelBufferPoolCreate(None, attrs)
    vcam._0x2f01cc(self_, 0)

    out = vcam.CVPixelBufferPoolCreatePixelBuffer(None, self_.pool, None)
    if not out:
        out = vcam.CVPixelBufferCreate(None, self_.out_w, self_.out_h,
                                       self_.out_pix_fmt, None, 0, None, None)

    vcam.sws_freeContext(self_.sws_ctx)
    self_.sws_ctx = vcam.sws_getContext(
        self_.out_w, self_.out_h, frame.src_pix_fmt,
        self_.out_pix_fmt, vcam.SWS_BILINEAR,
        frame.src_w, frame.src_h)

    vcam.CVPixelBufferLockBaseAddress(out, 0)
    dst        = vcam.CVPixelBufferGetBaseAddress(out)
    dst_stride = vcam.CVPixelBufferGetBytesPerRow(out)

    vcam.sws_scale(self_.sws_ctx,
                   (frame.data[0], frame.data[1], frame.data[2],
                    frame.linesize[0], frame.linesize[1], frame.linesize[2]),
                   0, frame.src_h, dst, vcam.SWS_BILINEAR)

    vcam.CVPixelBufferUnlockBaseAddress(out, 0)
    vcam.sws_freeContext(self_.sws_ctx)
    vcam.CVPixelBufferRelease(out)
    return out


# ---------------------------------------------------------------------------
# 重开流
# ---------------------------------------------------------------------------
def reopen_stream(vcam, self_):
    vcam.avcodec_flush_buffers(self_.video_codec_ctx)
    vcam.avcodec_flush_buffers(self_.audio_codec_ctx)
    vcam.avformat_close_input(self_.fmt_ctx)
    vcam.avcodec_free_context(self_.video_codec_ctx)
    vcam.avcodec_free_context(self_.audio_codec_ctx)
    vcam.av_buffer_unref(self_.hw_device_ref)
    vcam.swr_free(self_.swr)

    self_.fmt_ctx = vcam.avformat_alloc_context()

    opts = vcam.av_dict_new()
    for k, v in self_.input_options:
        vcam.av_dict_set(opts, k, v, 0)
        vcam.objc_retain(v)

    ret = vcam.avformat_open_input(self_.fmt_ctx, self_.url, None, opts)
    vcam.av_dict_free(opts)
    if ret < 0:
        vcam.objc_msgSend(self_, "reportError:",
                          vcam.av_strerror(ret, vcam.err_buf, 64))
        return False

    vcam.avformat_find_stream_info(self_.fmt_ctx, None)
    self_.video_stream_index = vcam.av_find_best_stream(
        self_.fmt_ctx, vcam.AVMEDIA_TYPE_VIDEO)
    self_.audio_stream_index = vcam.av_find_best_stream(
        self_.fmt_ctx, vcam.AVMEDIA_TYPE_AUDIO)

    self_.video_par = vcam.av_codec_parameters(
        self_.fmt_ctx.streams[0])
    self_.duration = vcam.av_format_duration(
        self_.fmt_ctx, vcam.AV_TIME_BASE_Q)

    vcam._0x2aa134(self_)
    return True


def cleanup_ffmpeg(vcam, self_):
    if self_.sws_ctx is not None:
        vcam.sws_freeContext(self_.sws_ctx)
        self_.sws_ctx = None
    if self_.swr is not None:
        vcam.swr_free(self_.swr)
        self_.swr = None
    if self_.video_codec_ctx is not None:
        vcam.avcodec_free_context(self_.video_codec_ctx)
    if self_.audio_codec_ctx is not None:
        vcam.avcodec_free_context(self_.audio_codec_ctx)
    if self_.hw_device_ref is not None:
        vcam.av_buffer_unref(self_.hw_device_ref)
    if self_.fmt_ctx is not None:
        vcam.avformat_close_input(self_.fmt_ctx)
    if self_.pool is not None:
        vcam.CVPixelBufferPoolRelease(self_.pool)
        self_.pool = None


# ---------------------------------------------------------------------------
# 状态与错误上报
# ---------------------------------------------------------------------------
def update_state(vcam, self_, state):
    self_.state = state
    queue = vcam.dispatch_get_main_queue()
    vcam.dispatch_async(queue, lambda: vcam._notify_state(self_))


def report_error(vcam, self_, message):
    self_.last_error = message
    vcam.objc_msgSend(self_, "updateState:", _State.ERROR)

    d = vcam.objc_loadWeakRetained(vcam._delegate_ref(self_))
    if d is not None:
        if vcam.objc_msgSend(d, "respondsToSelector:",
                             "ffplayer:didEncounterError:"):
            queue = vcam.dispatch_get_main_queue()
            vcam.dispatch_async(queue,
                                lambda: vcam.objc_msgSend(
                                    d, "ffplayer:didEncounterError:",
                                    self_, message))
    vcam.objc_release(d)
    vcam._clear_ivar_state(self_)
    return None


# ---------------------------------------------------------------------------
# 访问器
# ---------------------------------------------------------------------------
ACCESSORS = (
    ("delegate",      "setDelegate:",      0x2f48f0, 0x2f4958),
    ("state",         "setState:",         0x2f49c0, 0x2f4a24),
    ("isPlaying",     "setIsPlaying:",     0x2f4a88, 0x2f4af0),
    ("audioMuted",    "setAudioMuted:",    0x2f4b60, 0x2f4bc8),
    ("loopEnabled",   "setLoopEnabled:",   0x2f4c38, 0x2f4ca0),
    ("currentTime",   "setCurrentTime:",   0x2f4d10, 0x2f4d74),
    ("duration",      "setDuration:",      0x2f4dd8, 0x2f4e3c),
    ("videoSize",     "setVideoSize:",     0x2f4ea0, 0x2f4f18),
    ("hasVideo",      "setHasVideo:",      0x2f4f80, 0x2f4fe8),
    ("hasAudio",      "setHasAudio:",      0x2f5058, 0x2f50c0),
    ("isLiveStream",  "setIsLiveStream:",  0x2f5130, 0x2f5198),
)


def make_accessors(vcam):
    out = {}
    for name, setter, gaddr, saddr in ACCESSORS:
        out[name]   = _make_getter(vcam, name, gaddr)
        out[setter] = _make_setter(vcam, name, saddr)
    return out


def _make_getter(vcam, name, addr):
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
    raise NotImplementedError("ARC ivar 释放序列")
