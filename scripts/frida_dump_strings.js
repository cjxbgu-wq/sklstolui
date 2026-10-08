/*
 * frida_dump_strings.js — 去混淆字符串运行时校验
 *
 * 校验真机解密结果与静态 replay 是否逐字节一致；
 * 核对每个块的一次性 __bss 标志；
 * 取回静态无法判定为字符串的分散/半字写入目标。
 *
 * 用法:
 *   frida -U -f <宿主App> -l frida_dump_strings.js
 */
'use strict';

// 全部解密块：entry, size, one-shot __bss flag, 目标区间
const DEOBF_SITES = [
  [0x00276ed4,   3556, 0x14e0b94, 0x3f66d2, 0x3f67b0],
  [0x00277cb8,    616, 0x14e0b98, 0x3f68ce, 0x3f68db],
  // ... （其余与上一版一致）
];

// 解密目标写入区间（覆盖 10 个页）
const DATA_LO = 0x3f66d2;
const DATA_HI = 0x40006d;

// 期望的字符串明文：struct 本体 -> { ptr, len, isa, text, enc }
const CFSTRINGS = {
  0x003f67e0: { isa: 0x7c8, ptr: 0x003f66d2, len: 1, enc: "utf8", text: "B" },
  0x003f6820: { isa: 0x7c8, ptr: 0x003f6721, len: 11, enc: "utf8", text: "tencent.xin" },
  // ... （其余与上一版一致）
};

// 不产出可读字符串的块（二进制表/密钥/状态变量）
const NON_STRING_BLOCKS = {
  0x002983dc: 0x14e1240,
  0x0029c0c8: 0x14e12d4,
  // ... （其余与上一版一致）
};

function hex(b) {
  const out = [];
  for (let i = 0; i < b.length; i++) out.push(b[i].toString(16).padStart(2, '0'));
  return out.join(' ');
}

function readU16LE(b) {
  const u = [];
  for (let i = 0; i + 1 < b.length; i += 2) u.push(b[i] | (b[i + 1] << 8));
  return u;
}

function utf16ToStr(u) {
  let out = '';
  for (let i = 0; i < u.length; i++) {
    const c = u[i];
    if (c === 0) continue;
    if (c >= 0xd800 && c <= 0xdbff && i + 1 < u.length &&
        u[i + 1] >= 0xdc00 && u[i + 1] <= 0xdfff) {
      const cp = ((c - 0xd800) << 10) + (u[i + 1] - 0xdc00) + 0x10000;
      out += String.fromCodePoint(cp);
      i++;
    } else {
      out += String.fromCharCode(c);
    }
  }
  return out;
}

function tryUtf8(b) {
  try { return decodeURIComponent(escape(b)); } catch (e) { return null; }
}

function trimNul(b) {
  let n = b.length;
  while (n > 0 && b[n - 1] === 0) n--;
  return b.subarray(0, n);
}

function printableAscii(b) {
  if (b.length === 0) return false;
  for (let i = 0; i < b.length; i++) {
    if (b[i] < 0x20 || b[i] > 0x7e) return false;
  }
  return true;
}

function utf16Printable(b) {
  const u = readU16LE(b);
  if (u.length === 0) return false;
  for (let i = 0; i < u.length; i++) {
    const c = u[i];
    if (c === 0) continue;
    if (c < 0x20 || (c > 0x7e && c < 0xa0)) return false;
  }
  return true;
}

const CFB_ISA_UTF8 = 0x7c8;
const CFB_ISA_UTF16 = 0x7d0;

function bodyLen(isa, len) {
  return isa === CFB_ISA_UTF16 ? 2 * len : len;
}

function decodeBody(raw, enc) {
  if (enc === 'utf16') return utf16ToStr(readU16LE(raw));
  return tryUtf8(raw);
}

function main() {
  const mod = Process.findModuleByName('Vacm_afasds.dylib') || Process.enumerateModules()[0];
  const base = mod.base;
  console.log(`module ${mod.name} base=${base} size=0x${mod.size.toString(16)}`);

  const rd = (vmaddr, n) => base.add(vmaddr).readByteArray(n);

  let mismatches = 0;
  let checked = 0;
  const seen = new Set();

  for (const [entry, size, flag, lo, hi] of DEOBF_SITES) {
    Interceptor.attach(base.add(entry), {
      onEnter() {
        let f = -1;
        try {
          const fb = new Uint8Array(rd(flag, 4));
          f = (fb[0] | (fb[1] << 8) | (fb[2] << 16) | (fb[3] << 24)) >>> 0;
        } catch (e) { }
        this.preFlag = f;
        this.ran = f === 0;
        seen.add(entry);
        try { this.snap = new Uint8Array(rd(lo, hi - lo + 1)); } catch (e) { this.snap = null; }
      },
      onLeave() {
        if (!this.ran) {
          console.log(`--- 0x${entry.toString(16)} SKIPPED (one-shot flag 0x${flag.toString(16)} already set)`);
          return;
        }
        const after = new Uint8Array(rd(lo, hi - lo + 1));
        const changed = [];
        for (let i = 0; i < after.length; i++) {
          if (this.snap && after[i] !== this.snap[i]) {
            let j = i;
            while (j + 1 < after.length && after[j + 1] !== this.snap[j + 1]) j++;
            changed.push([lo + i, lo + j]);
            i = j;
          }
        }
        console.log(`\n--- 0x${entry.toString(16)} (${size}B) flag 0x${flag.toString(16)}` +
                    ` -> ${changed.length} run(s) in 0x${lo.toString(16)}..0x${hi.toString(16)}`);
        for (const [a0, a1] of changed) {
          const raw = trimNul(after.subarray(a0 - lo, a1 - lo + 1));
          if (raw.length === 0) {
            console.log(`  NUL 0x${a0.toString(16)}..0x${a1.toString(16)} (仅终止符)`);
            continue;
          }
          let txt = null, enc = null;
          if (printableAscii(raw)) { txt = tryUtf8(raw); enc = 'utf8'; }
          else if (utf16Printable(raw)) { txt = decodeBody(raw, 'utf16'); enc = 'utf16'; }
          const tag = txt !== null ? enc.toUpperCase() : 'BIN';
          console.log(`  ${tag} 0x${a0.toString(16)}..0x${a1.toString(16)} ` +
                      `len=${raw.length}  ${txt !== null ? JSON.stringify(txt) : hex(raw)}`);
        }
      }
    });
  }

  setTimeout(() => {
    console.log('\n===== CFConstantString 表核对 =====');
    for (const a of Object.keys(CFSTRINGS).map(Number).sort((x, y) => x - y)) {
      const rec = CFSTRINGS[a];
      let got = null;
      try {
        const n = bodyLen(rec.isa, rec.len);
        const raw = new Uint8Array(rd(rec.ptr, n));
        const tail = new Uint8Array(rd(rec.ptr + n, rec.enc === 'utf16' ? 2 : 1));
        let nulOk = false;
        if (rec.enc === 'utf16') {
          nulOk = tail.length === 2 && tail[0] === 0 && tail[1] === 0;
        } else {
          nulOk = tail.length === 1 && tail[0] === 0;
        }
        got = nulOk ? decodeBody(raw, rec.enc) : '<missing trailing NUL>';
      } catch (e) { got = '<read failed: ' + e.message + '>'; }
      checked++;
      const ok = got === rec.text;
      if (!ok) mismatches++;
      console.log(`  ${ok ? 'OK  ' : 'DIFF'} struct 0x${a.toString(16)} ` +
                  `isa=0x${rec.isa.toString(16)} ptr 0x${rec.ptr.toString(16)} ` +
                  `len ${rec.len} [${rec.enc}] got ${JSON.stringify(got)}` +
                  (ok ? '' : `  want ${JSON.stringify(rec.text)}`));
    }

    console.log('\n===== 运行时填充槽位 =====');
    for (const extra of [0x3f61a0]) {
      try {
        console.log(`0x${extra.toString(16)}: ${hex(new Uint8Array(rd(extra, 48)))}`);
      } catch (e) {
        console.log(`0x${extra.toString(16)}: <unreadable> ${e.message}`);
      }
    }

    const missed = DEOBF_SITES.filter(s => !seen.has(s[0]));
    console.log(`\n块覆盖: ${seen.size}/${DEOBF_SITES.length}` +
                (missed.length ? ` 未触发: ${missed.map(s => '0x' + s[0].toString(16)).join(', ')}` : ''));
    console.log(`字符串核对: ${checked - mismatches}/${checked} 一致` +
                (mismatches ? `  (${mismatches} 处不一致)` : '  [全部一致]'));
    console.log(`不产出字符串的块: ${Object.keys(NON_STRING_BLOCKS).length}`);
  }, 5000);
}

setImmediate(main);
