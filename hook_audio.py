# -*- coding: utf-8 -*-
"""
hook_audio.py — VCam 音频注入子系统。

包含原 IMP 注册表、带锁音频缓冲、hook 安装三件套（swizzle / replace-only /
orchestrator）、capture delegate 蹦床、MTAudioProcessingTap 宿主、
AVAudioEngine 播放侧、AVAudioPCMBuffer 渲染、AudioUnit 转换、
AVCaptureSession 采集链、FFmpeg 音频帧落地、菜单开关。
"""

ADDR_AV_AUDIO_ENGINE_SETUP     = 0x2AAAD0
ADDR_AV_PCM_BUFFER_RENDER      = 0x2AAD40
ADDR_MTA_TAP_SETUP             = 0x2AB370
ADDR_MTA_GET_SOURCE_AUDIO      = 0x2ABD00
ADDR_AUDIO_UNIT_PATH           = 0x2AC510
ADDR_CAPTURE_SESSION_BUILD     = 0x2AD930
ADDR_AUDIO_DELEGATE_TRAMPOLINE = 0x2AF638
ADDR_GET_ORIGINAL_AUDIO_IMP    = 0x2AF638
ADDR_INSTALL_AUDIO_HOOK        = 0x287FC4

IMP_GET_ORIGINAL_AUDIO_IMP   = 0x2811C0
IMP_SET_ORIGINAL_AUDIO_IMP   = 0x2812AC
IMP_IS_AUDIO_HOOKED          = 0x281398
IMP_AUDIO_INJECT_ENABLED     = 0x282938
IMP_SET_AUDIO_INJECT_ENABLED = 0x2829A0
IMP_CACHED_AUDIO_BUFFER      = 0x28454C
IMP_SET_CACHED_AUDIO_BUFFER  = 0x2845B0
IMP_AUDIO_BUFFER_LOCK        = 0x284614
IMP_CLEAR_AUDIO_BUFFER       = 0x2815DC
IMP_DID_OUTPUT_AUDIO_DATA    = 0x27B640

IMP_SETUP_AUDIO_DECODER = 0x2F0248
IMP_READ_LOOP           = 0x2F04E0
IMP_HANDLE_AUDIO_FRAME  = 0x2F1368

IMP_MUTE_TAPPED         = 0x296700
IMP_AUDIO_INJECT_TAPPED = 0x2969C8


class AudioImpRegistry:
    """originalIMPs: NSMutableDictionary，key=类名，value=原 IMP。"""

    def __init__(self, vcam):
        self._storage = vcam.objc_msgSend("_OBJC_CLASS_$_NSMutableDictionary", "new")

    def get(self, class_name):
        return self._storage.objectForKey_(class_name)

    def set(self, imp, class_name):
        self._storage.setObject_forKey_(imp, class_name)

    def is_audio_hooked(self, class_name):
        return bool(self._storage.objectForKey_(class_name))

    def clear(self):
        self._storage.removeAllObjects()


class CachedAudioBuffer:
    """跨线程共享的最近一帧音频 CMSampleBuffer / AVAudioPCMBuffer。"""

    def __init__(self, vcam):
        self._vcam   = vcam
        self._buffer = None
        self._lock   = vcam.objc_alloc_init("_OBJC_CLASS_$_NSLock")

    def get(self):
        with self._lock:
            return self._buffer

    def set(self, buffer):
        with self._lock:
            self._buffer = buffer

    def clear(self):
        self._lock.lock()
        old = self._buffer
        self._buffer = None
        if old is not None:
            self._vcam.CFRelease(old)
        self._lock.unlock()

    @property
    def lock(self):
        return self._lock


def replace_instance_method(vcam, cls, selector, new_imp):
    """只替换不交换，返回被替换掉的原 IMP。"""
    m        = vcam.class_getInstanceMethod(cls, selector)
    types    = vcam.method_getTypeEncoding(m)
    old_imp  = vcam.method_getImplementation(m)
    vcam.class_replaceMethod(cls, selector, new_imp, types)
    return old_imp


def swizzle_setSampleBufferDelegate_audio(vcam, obj):
    """交换 setSampleBufferDelegate:queue: 与 vcam_ 别名。"""
    cls = vcam.objc_msgSend(obj, "class")
    m_orig  = vcam.class_getInstanceMethod(cls, "setSampleBufferDelegate:queue:")
    m_new   = vcam.class_getInstanceMethod(
        cls, "vcam_setAudioSampleBufferDelegate:queue:")

    cls = vcam.objc_msgSend(obj, "class")
    orig_imp   = vcam.method_getImplementation(m_orig)
    orig_types = vcam.method_getTypeEncoding(m_orig)

    if not vcam.class_getInstanceMethod(m_new):
        vcam.class_addMethod(cls, "vcam_setAudioSampleBufferDelegate:queue:",
                             orig_imp, orig_types)

    cls = vcam.objc_msgSend(obj, "class")
    m_new = vcam.class_getInstanceMethod(
        cls, "vcam_setAudioSampleBufferDelegate:queue:")
    new_imp   = vcam.method_getImplementation(m_new)
    new_types = vcam.method_getTypeEncoding(m_new)

    vcam.class_replaceMethod(cls, "setSampleBufferDelegate:queue:",
                             new_imp, new_types)
    vcam.method_exchangeImplementations(m_orig, m_new)


def install_audio_hook(vcam, obj, delegate, queue):
    """安装音频 hook：先 swizzle，再登记原 IMP，再装 delegate。"""
    swizzle_setSampleBufferDelegate_audio(vcam, obj)

    vcam_shared = vcam.objc_msgSend(_CLASS_A3F9C1E2, "shared")
    cls2        = vcam.objc_msgSend(obj, "class")
    class_name  = vcam.NSStringFromClass(cls2)

    already       = vcam.objc_msgSend(vcam_shared, "isHooked:", class_name)
    already_audio = vcam.objc_msgSend(vcam_shared, "isAudioHooked:", class_name)
    if already or already_audio:
        return

    host_cls = vcam.objc_msgSend(obj, "class")
    orig_cb_imp = replace_instance_method(
        vcam, host_cls,
        "captureOutput:didOutputSampleBuffer:fromConnection:",
        vcam.audio_capture_trampoline)

    vcam.objc_msgSend(vcam_shared,
                      "setOriginalAudioIMP:forClass:",
                      orig_cb_imp, class_name)

    vcam.objc_msgSend(obj, "vcam_setAudioSampleBufferDelegate:queue:",
                      delegate, queue)


def capture_output_did_output_sample_buffer(vcam, output, sample_buffer, connection):
    """音频 sample buffer 拦截点：缓存该帧并转发给原 IMP。"""
    cls        = vcam.objc_msgSend(output, "class")
    class_name = vcam.objc_msgSend(cls, "NSStringFromClass")
    vcam_shared = vcam.objc_msgSend(_CLASS_A3F9C1E2, "shared")

    orig_imp = vcam.objc_msgSend(vcam_shared,
                                 "getOriginalAudioIMPForClass:", class_name)

    av_class = vcam.objc_msgSend(_CLASS_AVCAPTUREAUDIODATAOUTPUT, "class")
    if vcam.objc_msgSend(output, "isKindOfClass:", av_class):
        vcam.objc_msgSend(vcam_shared, "cachedAudioBuffer")
        vcam_shared.setCachedAudioBuffer_(sample_buffer)

    if orig_imp is not None:
        orig_imp(output,
                 "captureOutput:didOutputSampleBuffer:fromConnection:",
                 sample_buffer, connection)


class MTAudioProcessingTapContext:
    """MTAudioProcessingTap 的宿主与回调表。"""

    def __init__(self, tap):
        self.tap = tap
        self.stream_description = None
        self.buffer_list = None

    def get_source_audio(self, tap, flags, out_asbd, out_buffer_list):
        return _MTAudioProcessingTapGetSourceAudio(
            tap, flags, out_asbd, out_buffer_list)

    def process_tap(self, owner, asbd, frames, audio_buffer_list, time_range, flags):
        if not _VCAM_SHARED.audioInjectEnabled():
            return
        # 逐样本增益/重采样位于 XOR 混淆区，运行时由 Frida 补全
        for i in range(frames):
            pass
        _VCAM_SHARED.setCachedAudioBuffer_(audio_buffer_list)


def build_av_audio_engine(vcam, sample_rate, channels):
    engine = vcam.objc_msgSend(_CLASS_AVAUDIOENGINE, "alloc")
    engine = vcam.objc_msgSend(engine, "init")

    player_node = vcam.objc_msgSend(_CLASS_AVAUDIOPLAYERNODE, "alloc")
    player_node = vcam.objc_msgSend(player_node, "init")

    fmt = vcam.objc_msgSend(_CLASS_AVAUDIOFORMAT, "alloc")
    fmt = vcam.objc_msgSend(fmt, "initWithCommonFormat:sampleRate:channels:",
                            _AVFLOAT32, sample_rate, channels)

    vcam.objc_msgSend(engine, "attachNode:", player_node)
    vcam.objc_msgSend(engine, "connect:toFormat:fromBus:", player_node, fmt, 0)
    return engine, player_node, fmt


def render_pcm_buffer(vcam, format_, frames):
    pcm = vcam.objc_msgSend(_CLASS_AVAUDIOPCMBUFFER, "alloc")
    pcm = vcam.objc_msgSend(pcm, "initWithPCMFormat:frameCapacity:",
                            format_, frames)

    cached = _VCAM_SHARED.cachedAudioBuffer()
    if cached is None:
        _VCAM_SHARED.clearAudioBuffer()
        return None
    pcm.frameLength = frames
    return pcm


def audio_unit_convert(vcam, in_asbd, in_frames, out_asbd):
    """AudioUnit 音频格式转换；具体 AU 子类型需运行时补全。"""
    return None


def build_capture_audio_session(vcam, device):
    device_input = vcam.objc_msgSend(_CLASS_AVCAPTUREDEVICEINPUT, "alloc")
    device_input = vcam.objc_msgSend(device_input, "initWithDevice:error:",
                                     device, None)

    audio_output = vcam.objc_msgSend(_CLASS_AVCAPTUREAUDIODATAOUTPUT, "alloc")
    audio_output = vcam.objc_msgSend(audio_output, "init")

    session = None

    vcam.objc_msgSend(audio_output, "setSampleBufferDelegate:queue:",
                      _VCAM_SHARED, _QUEUE_AUDIO)
    return session, device_input, audio_output


def ffplayer_did_output_audio_data(vcam, player, data, frames, pts):
    self._audio_data   = data
    self._audio_frames = frames
    self._audio_pts    = pts
    return None


def mute_tapped(vcam):
    current = _VCAM_SHARED.audioInjectEnabled()
    _VCAM_SHARED.setAudioInjectEnabled_(not current)
    if current:
        _VCAM_SHARED.clearAudioBuffer()
    return not current


def audio_inject_tapped(vcam):
    current = _VCAM_SHARED.audioInjectEnabled()
    _VCAM_SHARED.setAudioInjectEnabled_(not current)
    if not current:
        install_audio_hook(vcam, _CAPTURE_AUDIO_OUTPUT,
                           _VCAM_SHARED, _QUEUE_AUDIO)
        _MTA_TAP.get_source_audio(_MTA_TAP.tap, 0,
                                  _MTA_TAP.stream_description,
                                  _MTA_TAP.buffer_list)
    else:
        _VCAM_SHARED.clearAudioBuffer()
    return not current


def bind(vcam_shared, queue_audio):
    global _VCAM_SHARED, _QUEUE_AUDIO
    _VCAM_SHARED = vcam_shared
    _QUEUE_AUDIO = queue_audio


_CLASS_A3F9C1E2                = "_OBJC_CLASS_$__0xA3F9c1E2"
_CLASS_8B3E5D1F                = "_OBJC_CLASS_$__0x8B3e5D1F"
_CLASS_AVAUDIOENGINE           = "_OBJC_CLASS_$_AVAudioEngine"
_CLASS_AVAUDIOPLAYERNODE       = "_OBJC_CLASS_$_AVAudioPlayerNode"
_CLASS_AVAUDIOFORMAT           = "_OBJC_CLASS_$_AVAudioFormat"
_CLASS_AVAUDIOPCMBUFFER        = "_OBJC_CLASS_$_AVAudioPCMBuffer"
_CLASS_AVCAPTUREDEVICEINPUT    = "_OBJC_CLASS_$_AVCaptureDeviceInput"
_CLASS_AVCAPTUREAUDIODATAOUTPUT = "_OBJC_CLASS_$_AVCaptureAudioDataOutput"

_AVFLOAT32 = 0x4

_VCAM_SHARED          = None
_QUEUE_AUDIO          = None
_CAPTURE_AUDIO_OUTPUT = None
_MTA_TAP              = None

_MTAudioProcessingTapGetSourceAudio = None
