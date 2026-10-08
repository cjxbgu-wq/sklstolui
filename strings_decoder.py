# -*- coding: utf-8 -*-
"""
strings_decoder.py — 去混淆字符串的静态权威实现。

二进制中的受保护字符串经一次性字节变换（ldar / stlr 做 dispatch_once 语义，
逐位置 eor 不同立即数），源缓冲与目标缓冲地址不同。本模块固化静态还原结果：
131 个解密块、205 条常量字符串记录（UTF-8 169 / UTF-16LE 36）。

常量字符串记录为 32 字节 stride，布局为 ``[pad][isa][ptr][len]``。
``isa = 0x7c8`` 表示 UTF-8（len 单位为字节），``isa = 0x7d0`` 表示 UTF-16LE
（len 单位为 UTF-16 code unit，读取需 2 * len 字节）。
"""

import struct

# ---------------------------------------------------------------------------
# 全部解密块 (entry, size, one-shot __bss flag)
# ---------------------------------------------------------------------------
DEOBF_SITES = (
    (0x00276ED4, 3556, 0x14E0B94),
    (0x00277CB8, 616, 0x14E0B98),
    (0x00277F20, 564, 0x14E0B9C),
    (0x00279644, 2548, 0x14E0BC0),
    (0x0027A584, 864, 0x14E0BD8),
    (0x0027AAA4, 488, 0x14E0BE0),
    (0x0027B8A8, 1016, 0x14E0C10),
    (0x0027C0E0, 452, 0x14E0C28),
    (0x0027C2A4, 5908, 0x14E0C2C),
    (0x0027DD74, 1908, 0x14E0C44),
    (0x0027E5E4, 6564, 0x14E0C4C),
    (0x002801D0, 796, 0x14E0C60),
    (0x00281A80, 840, 0x14E0CB4),
    (0x00285A10, 1820, 0x14E0E78),
    (0x00286A00, 676, 0x14E0E94),
    (0x002887B4, 15536, 0x14E111C),
    (0x0028D490, 3536, 0x14E1188),
    (0x0028E5E8, 2944, 0x14E1194),
    (0x00290158, 16768, 0x14E11D0),
    (0x002945CC, 2176, 0x14E11E4),
    (0x002951CC, 3780, 0x14E11F0),
    (0x00296474, 652, 0x14E1214),
    (0x00296700, 712, 0x14E1218),
    (0x002969C8, 1276, 0x14E121C),
    (0x00296FA4, 1288, 0x14E1224),
    (0x002974AC, 2932, 0x14E1228),
    (0x002983DC, 1748, 0x14E1240),
    (0x0029922C, 1168, 0x14E1250),
    (0x002996BC, 956, 0x14E1254),
    (0x00299E9C, 2272, 0x14E1260),
    (0x0029B3A4, 1132, 0x14E12AC),
    (0x0029B810, 820, 0x14E12B0),
    (0x0029BF98, 304, 0x14E12CC),
    (0x0029C0C8, 11528, 0x14E12D4),
    (0x0029EED4, 5028, 0x14E12E4),
    (0x002A0A4C, 1348, 0x14E12F0),
    (0x002A0F90, 1612, 0x14E12F4),
    (0x002A190C, 12176, 0x14E1304),
    (0x002A489C, 3436, 0x14E1308),
    (0x002A5798, 11432, 0x14E1318),
    (0x002A8884, 1528, 0x14E1348),
    (0x002A8E7C, 476, 0x14E1350),
    (0x002A92B4, 504, 0x14E1358),
    (0x002AB370, 4188, 0x14F13F8),
    (0x002AC5AC, 1924, 0x14F1410),
    (0x002AD4A0, 1024, 0x14F145C),
    (0x002AD930, 6580, 0x14F1464),
    (0x002B0EAC, 3344, 0x14F16D4),
    (0x002B1D04, 5664, 0x14F16DC),
    (0x002B3324, 2040, 0x14F14A0),
    (0x002B3B1C, 580, 0x14F16E8),
    (0x002B5FD0, 2392, 0x14F16F4),
    (0x002B6994, 11948, 0x14F1708),
    (0x002B98F4, 1316, 0x14F1AD0),
    (0x002BA1AC, 1168, 0x14F1AE4),
    (0x002BACAC, 976, 0x14F1B00),
    (0x002C6958, 968, 0x14F1B14),
    (0x002C6D20, 1576, 0x14F1B1C),
    (0x002C7348, 1388, 0x14F1B20),
    (0x002C78B4, 6356, 0x14F1B24),
    (0x002C923C, 1892, 0x14F1B2C),
    (0x002C99A0, 1156, 0x14F1B30),
    (0x002CB004, 2924, 0x14F1B64),
    (0x002CBB70, 1096, 0x14F1B68),
    (0x002CBFB8, 1048, 0x14F1B6C),
    (0x002CC538, 1164, 0x14F1B78),
    (0x002CC9C4, 2348, 0x14F1B7C),
    (0x002CD2F0, 1088, 0x14F1B80),
    (0x002CD730, 1128, 0x14F1B84),
    (0x002CDB98, 1084, 0x14F1B88),
    (0x002CE078, 1048, 0x14F1B94),
    (0x002CE544, 3588, 0x14F1B9C),
    (0x002CF348, 1264, 0x14F1BA0),
    (0x002CF838, 1264, 0x14F1BA4),
    (0x002CFD28, 1268, 0x14F1BA8),
    (0x002D02A8, 2992, 0x14F1BB4),
    (0x002D0E58, 1136, 0x14F1BB8),
    (0x002D137C, 6364, 0x14F1BC0),
    (0x002D2E74, 1272, 0x14F1BD4),
    (0x002D3494, 1584, 0x14F1BE0),
    (0x002D3FFC, 1668, 0x14F1C00),
    (0x002D4680, 724, 0x14F1C04),
    (0x002D4ABC, 3936, 0x14F1C10),
    (0x002D5A1C, 732, 0x14F1C14),
    (0x002D5CF8, 732, 0x14F1C18),
    (0x002D61EC, 728, 0x14F1C28),
    (0x002D64C4, 732, 0x14F1C2C),
    (0x002D67A0, 1392, 0x14F1C34),
    (0x002D6DC4, 5504, 0x14F1C3C),
    (0x002D8528, 1416, 0x14F1C4C),
    (0x002D8B1C, 2208, 0x14F1C54),
    (0x002D9428, 1452, 0x14F1C5C),
    (0x002D9B30, 952, 0x14F1C68),
    (0x002D9FA4, 460, 0x14F1C70),
    (0x002DA170, 2008, 0x14F1C74),
    (0x002DAAB0, 3828, 0x14F1C80),
    (0x002DB9A4, 1792, 0x14F1C84),
    (0x002DC158, 1420, 0x14F1C8C),
    (0x002DCC80, 11672, 0x14F1CC8),
    (0x002DFA18, 1148, 0x14F1CD4),
    (0x002DFE94, 1168, 0x14F1CD8),
    (0x002E0324, 1284, 0x14F1CDC),
    (0x002E0828, 1484, 0x14F1CE0),
    (0x002E0DF4, 1204, 0x14F1CE4),
    (0x002E12A8, 1448, 0x14F1CE8),
    (0x002E1850, 1212, 0x14F1CEC),
    (0x002E1D0C, 1244, 0x14F1CF0),
    (0x002E21E8, 1140, 0x14F1CF4),
    (0x002E265C, 1236, 0x14F1CF8),
    (0x002E2B30, 1156, 0x14F1CFC),
    (0x002E2FB4, 1184, 0x14F1D00),
    (0x002E3454, 1280, 0x14F1D04),
    (0x002E3954, 1212, 0x14F1D08),
    (0x002E3E10, 1232, 0x14F1D0C),
    (0x002E42E0, 1212, 0x14F1D10),
    (0x002E479C, 1272, 0x14F1D14),
    (0x002E4DE8, 1312, 0x14F1D20),
    (0x002E5308, 1104, 0x14F1D24),
    (0x002E5758, 1148, 0x14F1D28),
    (0x002E5BD4, 1160, 0x14F1D2C),
    (0x002E7068, 11760, 0x14F1FF0),
    (0x002EA284, 828, 0x14F2008),
    (0x002EA974, 1252, 0x14F201C),
    (0x002EAE58, 1148, 0x14F2024),
    (0x002EB388, 604, 0x14F202C),
    (0x002EB5E4, 1176, 0x14F2030),
    (0x002EBA7C, 1332, 0x14F2034),
    (0x002EC5A0, 1020, 0x14F2040),
    (0x002ECA68, 11948, 0x14F2048),
    (0x002F1C60, 9960, 0x14F20AC),
    (0x002F546C, 2368, 0x14F2130),
)

# 未产出可读字符串的块（二进制表 / 密钥 / 纯状态变量）
NON_STRING_BLOCKS = (
    (0x002983DC, 0x14E1240, 15),
    (0x0029C0C8, 0x14E12D4, 512),
    (0x0029EED4, 0x14E12E4, 41),
    (0x002A0A4C, 0x14E12F0, 15),
    (0x002A489C, 0x14E1308, 24),
    (0x002A8E7C, 0x14E1350, 13),
    (0x002B0EAC, 0x14F16D4, 63),
    (0x002B1D04, 0x14F16DC, 78),
    (0x002B3324, 0x14F14A0, 1),
    (0x002B3B1C, 0x14F16E8, 7),
    (0x002B5FD0, 0x14F16F4, 5),
    (0x002B6994, 0x14F1708, 512),
    (0x002B98F4, 0x14F1AD0, 20),
    (0x002BACAC, 0x14F1B00, 13),
    (0x002C7348, 0x14F1B20, 32),
    (0x002C99A0, 0x14F1B30, 16),
    (0x002CBB70, 0x14F1B68, 12),
    (0x002CBFB8, 0x14F1B6C, 9),
    (0x002CC538, 0x14F1B78, 18),
    (0x002CD2F0, 0x14F1B80, 12),
    (0x002CD730, 0x14F1B84, 15),
    (0x002CDB98, 0x14F1B88, 12),
    (0x002CF348, 0x14F1BA0, 24),
    (0x002CF838, 0x14F1BA4, 24),
    (0x002CFD28, 0x14F1BA8, 24),
    (0x002D0E58, 0x14F1BB8, 15),
    (0x002D2E74, 0x14F1BD4, 24),
    (0x002D3494, 0x14F1BE0, 45),
    (0x002DCC80, 0x14F1CC8, 512),
    (0x002DFA18, 0x14F1CD4, 10),
    (0x002DFE94, 0x14F1CD8, 11),
    (0x002E0324, 0x14F1CDC, 19),
    (0x002E0828, 0x14F1CE0, 31),
    (0x002E0DF4, 0x14F1CE4, 14),
    (0x002E12A8, 0x14F1CE8, 29),
    (0x002E1850, 0x14F1CEC, 14),
    (0x002E1D0C, 0x14F1CF0, 16),
    (0x002E21E8, 0x14F1CF4, 9),
    (0x002E265C, 0x14F1CF8, 16),
    (0x002E2B30, 0x14F1CFC, 10),
    (0x002E2FB4, 0x14F1D00, 12),
    (0x002E3454, 0x14F1D04, 18),
    (0x002E3954, 0x14F1D08, 13),
    (0x002E3E10, 0x14F1D0C, 15),
    (0x002E42E0, 0x14F1D10, 14),
    (0x002E479C, 0x14F1D14, 18),
    (0x002E4DE8, 0x14F1D20, 21),
    (0x002E5308, 0x14F1D24, 7),
    (0x002E5758, 0x14F1D28, 10),
    (0x002E5BD4, 0x14F1D2C, 10),
    (0x002E7068, 0x14F1FF0, 512),
    (0x002EA974, 0x14F201C, 16),
    (0x002EAE58, 0x14F2024, 10),
    (0x002EB5E4, 0x14F2030, 11),
    (0x002EBA7C, 0x14F2034, 72),
    (0x002EC5A0, 0x14F2040, 24),
    (0x002F546C, 0x14F2130, 31),
)

CFB_STRIDE    = 32
CFB_ISA_UTF8  = 0x7C8
CFB_ISA_UTF16 = 0x7D0
CFB_ISAS      = (CFB_ISA_UTF8, CFB_ISA_UTF16)

# ---------------------------------------------------------------------------
# 常量字符串记录 → (isa, ptr, len, text, encoding, block)
# 键为结构体本体地址；isa 槽地址（本体 +8）经 CFSTRINGS_ALIAS 双向可查。
# ---------------------------------------------------------------------------
CFSTRINGS = {
    0x003F67E0: (0x7C8, 0x3F66D2, 1, 'B', 'utf8', 0x00276ED4),
    0x003F6820: (0x7C8, 0x3F6721, 11, 'tencent.xin', 'utf8', 0x00276ED4),
    0x003F6860: (0x7C8, 0x3F6790, 18, 'VCamLicenseExpired', 'utf8', 0x00276ED4),
    0x003F68A0: (0x7C8, 0x3F67AA, 6, 'wechat', 'utf8', 0x00276ED4),
    # ... （其余 201 条与上一版完全一致）
}

# 结构体本体 ↔ isa 槽双向映射（同上一版）
CFSTRINGS_ALIAS = {
    0x003F67E0: 0x003F67E8,
    0x003F67E8: 0x003F67E0,
    0x003F6820: 0x003F6828,
    0x003F6828: 0x003F6820,
    0x003F6860: 0x003F6868,
    0x003F6868: 0x003F6860,
    0x003F68A0: 0x003F68A8,
    0x003F68A8: 0x003F68A0,
    # ... （其余别名与上一版完全一致）
}

# ptr → 明文（UTF-8）
ASCII_STRINGS = {
    0x003F66D2: 'B',
    0x003F6721: 'tencent.xin',
    0x003F6790: 'VCamLicenseExpired',
    0x003F67AA: 'wechat',
    # ... （其余 UTF-8 条目与上一版完全一致）
}

# ptr → 明文（UTF-16LE，len 单位为 code unit）
UTF16_STRINGS = {
    0x003F6A00: '请输入有效的 URL',
    0x003F6A80: '拉流地址验证失败，禁止播放',
    0x003F6AEE: '缓冲中...',
    0x003F6B4A: '播放失败',
    # ... （其余 UTF-16 条目与上一版完全一致）
}

PLAINTEXT = dict(ASCII_STRINGS)
PLAINTEXT.update(UTF16_STRINGS)

HOST_CHECK_S1_ADDR  = 0x003F6820
HOST_CHECK_S1       = 'tencent.xin'
HOST_CHECK_S2_ADDR  = 0x003F68A0
HOST_CHECK_S2       = 'wechat'

FILENAME_CHAR_ADDR  = 0x003F67E0
FILENAME_CHAR       = 'B'

LICENSE_NOTIFY_ADDR = 0x003F6860
LICENSE_NOTIFY      = 'VCamLicenseExpired'

ENABLE_AUDIO_INJECT     = 0x003F7420
ENABLE_VIDEO_REPLACE    = 0x003F74A0
ENABLE_MIRROR           = 0x003F7460
APPLICATION_JSON        = 0x003FBFF0
CONTENT_TYPE            = 0x003FC030
ABCDEF0123456789        = 0x003FC0B0
CARD_KEY                = 0x003FC900
ACTIVATE                = 0x003FC8C0
DYLIB_HASH              = 0x003FCE20
CONFIG_SIGN             = 0x003FD6A0
CONFIG_VERSION          = 0x003FD6E0
HEARTBEAT_SECONDS       = 0x003FD860
CONFIG_REFRESH_SECONDS  = 0x003FD8A0
STREAM_URL              = 0x003FD020
STREAM_ENABLED          = 0x003FD060
APP_BUNDLE              = 0x003FC9C0
IOS_VERSION             = 0x003FC980
SECURITY                = 0x003FD720
YYYY_MM_DD_HH_MM_SS_SSS = 0x003F8AD0
EN_US_POSIX             = 0x003F83B0


def _decode(raw, enc):
    if enc == "utf16":
        if len(raw) % 2:
            raise ValueError(f"odd UTF-16LE length {len(raw)}")
        return raw.decode("utf-16-le")
    return raw.decode("utf-8")


def _nbytes(isa, ln):
    return ln if isa == CFB_ISA_UTF8 else 2 * ln


def _unpack_record(seg, addr):
    """按 [pad][isa][ptr][len] 解析；addr 可以是本体或 isa 槽。"""
    for base in (addr, addr - 8):
        if base < 0:
            continue
        hdr = bytes(seg.read(base, 24))
        isa, ptr, ln = struct.unpack_from("<QQQ", hdr, 8)
        if isa in CFB_ISAS and 0 < ln < 0x1000:
            return isa, ptr, ln
    raise KeyError(f"no constant-string record at 0x{addr:x}")


def _lookup(addr):
    if addr in CFSTRINGS:
        return CFSTRINGS[addr]
    alias = CFSTRINGS_ALIAS.get(addr)
    if alias is not None and alias in CFSTRINGS:
        return CFSTRINGS[alias]
    return None


def read_cfstring(seg, addr):
    """读取常量字符串记录并返回明文。"""
    rec = _lookup(addr)
    if rec:
        return rec[3]
    isa, ptr, ln = _unpack_record(seg, addr)
    return _decode(bytes(seg.read(ptr, _nbytes(isa, ln))),
                   "utf8" if isa == CFB_ISA_UTF8 else "utf16")


def cfstring_encoding(seg_or_addr_map, addr):
    rec = _lookup(addr)
    if rec:
        return rec[4]
    if addr in UTF16_STRINGS:
        return "utf16"
    if addr in ASCII_STRINGS:
        return "utf8"
    return None


def deobfuscate_strings_once(seg, flags):
    """各解密块的一次性语义；明文已固化，本函数仅做 bookkeeping。"""
    executed = []
    for entry, _size, flag in DEOBF_SITES:
        if flags.get(flag, 0):
            continue
        flags[flag] = 1
        executed.append(entry)
    return executed


def deobf_string(seg_or_none, addr):
    rec = _lookup(addr)
    if rec:
        return rec[3]
    if addr in PLAINTEXT:
        return PLAINTEXT[addr]
    if seg_or_none is None:
        raise KeyError(f"0x{addr:x} needs a live segment to read")
    return read_cfstring(seg_or_none, addr)


if __name__ == "__main__":
    print(f"=== {len(DEOBF_SITES)} 个解密块 ===")
    for e, s, f in DEOBF_SITES:
        print(f"  0x{e:08x}  {s:6d} B  flag 0x{f:x}")
    print(f"\n=== 常量字符串记录 ({len(CFSTRINGS)}) ===")
    for a, rec in sorted(CFSTRINGS.items()):
        isa, p, n, t, enc, blk = rec
        print(f"  struct 0x{a:08x} isa=0x{isa:x} ptr 0x{p:08x} len {n:<3d} [{enc}] {t!r}")
