#!/usr/bin/env python3
"""XiaoXin 700-15ISK: 从 Windows Dolby(DAX2) 实测数据生成 EasyEffects 8 预设。

数据源：captures/loopback_pink_{off,dynamic,voice}.wav（WASAPI loopback 电域稳态）
曲线 = dynamic−off 的 20 带 PSD 差（= audio-optimizer 校正 + IEQ voicing 的合成，
与项目 DAX3 convolver 的输入同构）。L=R 差为 0，单 FIR 双声道共用。

复用 speaker-tuning-to-easyeffects 的 lib（make_fir 最小相位、make_convolver、
make_limiter、save_wav_stereo、kernel_name），零新增 DSP 假设。

v2 (2026-11)：响度校准与动态修正
  - makeup 不再取「peak_db - 1」：曲线峰值频段增益(+17dB) ≠ 宽带响度增益。
    实测 DAX2 粉噪(−18dBFS) ON/OFF 宽带 RMS 增益仅 +8.3dB（voice +6.2），
    峰值频段增益是「形状」，不是电平。makeup 直接用每档实测 RMS 增益。
  - limiter 只做 −1dBFS 顶棚：attack 5ms / release 150ms / lookahead 5ms /
    oversampling 8x（原 1/5/1/None 的组合做十几个 dB GR 会产生可闻调幅失真）。
  - 新增 compressor（th−22 / 1.5:1 / makeup +5 / atk 80ms / rel 500ms）：
    温和复刻 DAX2 的电平相关增益（实测轻档 +20.5dB vs 响档 +8.3dB），
    改善小音量可闻度，同时避免把底噪抬得刺耳。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import numpy as np
from scipy.signal import welch

REPO = Path(__file__).resolve().parents[1] / "speaker-tuning-to-easyeffects"
sys.path.insert(0, str(REPO))
from lib.preset import fir                       # noqa: E402
from lib.preset.bands import make_convolver      # noqa: E402
from lib.preset.plugins import make_limiter      # noqa: E402
from lib.preset.emit import save_wav_stereo, stereo_taps, kernel_name  # noqa: E402

HERE = Path(__file__).resolve().parent
CAP = HERE / "captures"
SR = 48000
BANDS = [47, 141, 234, 328, 469, 656, 844, 1031, 1313, 1688,
         2250, 3000, 3750, 4688, 5813, 7125, 9000, 11250, 13875, 19688]


def psd_db(fn: str) -> tuple[np.ndarray, np.ndarray]:
    from scipy.io import wavfile
    import warnings
    warnings.filterwarnings("ignore")
    sr, x = wavfile.read(CAP / fn)
    seg = x[int(6 * sr):int(11 * sr)].astype(np.float64)
    if seg.ndim > 1:
        seg = seg[:, 0]
    f, P = welch(seg, fs=sr, nperseg=16384, noverlap=8192)
    return f, 10 * np.log10(P + 1e-24)


def curve(on: str, off: str = "loopback_pink_off.wav") -> list[float]:
    f, g_on = psd_db(on)
    _, g_off = psd_db(off)
    d = g_on - g_off
    return [float(d[np.argmin(abs(f - b))]) for b in BANDS]


def rms_gain_db(on: str, off: str = "loopback_pink_off.wav",
                fallback: float = 8.3) -> float:
    """宽带响度增益 = ON/OFF 采样的 RMS 差（6–11s 窗）。

    这是 DAX2 在该档位的真实整体电平增益（含它自己的压限），
    实测：dynamic/movie ≈ +8.3，music ≈ +8.6，voice ≈ +6.2。
    峰值频段增益（曲线峰 +17dB）是形状，不能当电平用。
    """
    from scipy.io import wavfile
    import warnings
    warnings.filterwarnings("ignore")
    try:
        out = []
        for fn in (on, off):
            sr, x = wavfile.read(CAP / fn)
            seg = x[int(6 * sr):int(11 * sr)].astype(np.float64)
            if seg.ndim > 1:
                seg = seg[:, 0]
            out.append(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12))
        g = float(out[0] - out[1])
        return float(np.clip(g, 5.0, 12.0))   # 合理区间, 防坏采样
    except Exception as e:
        print(f"  ! 读取采样失败({e}), makeup 回退 {fallback} dB")
        return fallback


def make_compressor() -> dict:
    """温和的向上响度管理：小声段托底, 大声段柔压。

    实测 DAX2 电平相关增益：轻档 +20.5dB vs 响档 +8.3dB（差 12dB）。
    单带压缩器做不了 12dB 那么多而不动底噪, 这里取温和档：
    makeup +5dB, 1.3:1, th−22dBFS, 慢动作(80/500ms) —— 提升小音量
    可闻度且几乎不暴露底噪。想更接近 DAX2 可提高 makeup/ratio。
    """
    return {
        "bypass": False,
        "input-gain": 0.0,
        "output-gain": 0.0,
        "threshold": -22.0,
        "ratio": 1.3,
        "attack": 80.0,
        "release": 500.0,
        "knee": 6.0,
        "makeup": 5.0,
    }


def build(name: str, gains_db: list[float], makeup_db: float,
          out_root: Path, dry: bool = False) -> dict:
    freqs = np.array(BANDS, dtype=float)
    taps, peak_db = fir.make_fir(freqs, np.array(gains_db))
    # make_fir 把曲线整体压低了 peak_db（峰归一）。注意：这只影响「形状」的
    # 绝对电平，宽带响度还原由 makeup_db（实测 RMS 增益）负责——
    # 不能用 peak_db 直接补（实测会把宽带响度多推 ~8dB, 限制器重压出破音）。
    stem = kernel_name(name, stereo_taps(taps, taps))
    irs = out_root / "irs" / f"{stem}.irs"
    limiter = make_limiter(input_gain=makeup_db)
    limiter.update({"attack": 5.0, "release": 150.0,
                    "lookahead": 5.0, "oversampling": "8x"})
    preset = {
        "_generator": {"tool": "dax_measure/gen_xiaoxin_preset.py",
                       "source": "Windows WASAPI loopback, XiaoXin 700-15ISK DAX2",
                       "note": (f"curve peak {peak_db:+.1f} dB (形状); "
                                f"makeup {makeup_db:+.1f} dB (实测宽带响度增益); "
                                "compressor th-22/1.5:1/mk+5; "
                                "limiter -1dB attack5/rel150/lookahead5/8x")},
        "output": {
            "blocklist": [],
            "convolver#0": make_convolver(stem),
            "compressor#0": make_compressor(),
            "limiter#0": limiter,
            "plugins_order": ["convolver#0", "compressor#0", "limiter#0"],
        },
    }
    out_dir = out_root / "output"
    if not dry:
        (irs.parent).mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        save_wav_stereo(irs, taps, taps)
        (out_dir / f"{name}.json").write_text(json.dumps(preset, indent=4) + "\n")
    print(f"[{name}] peak={peak_db:+.2f} dB makeup={makeup_db:+.1f} dB -> "
          f"{out_dir / (name + '.json')}, irs/{stem}.irs")    # FIR 验证：设计曲线 vs 实际频响
    fft_f = np.fft.rfftfreq(fir.FIR_LENGTH, d=1.0 / SR)
    H = 20 * np.log10(np.abs(np.fft.rfft(taps)) + 1e-12)
    from lib.preset.fir import interpolate_curve_db
    tgt = interpolate_curve_db(freqs, np.array(gains_db) - peak_db, fft_f)
    err = np.abs(H - tgt)[(fft_f >= 40) & (fft_f <= 20000)]
    print(f"    FIR 拟合误差 40Hz-20kHz: max {err.max():.2f} dB, "
          f"RMS {np.sqrt((err**2).mean()):.2f} dB")
    return preset


def main() -> int:
    dry = "--dry-run" in sys.argv
    root = Path.home() / ".local/share/easyeffects"
    dyn = curve("loopback_pink_dynamic.wav")
    voi = curve("loopback_pink_voice.wav")
    mus = curve("loopback_pink_music.wav")
    mov = curve("loopback_pink_movie.wav")
    print("实测 20 带差 (dB):")
    for label, c in (("dynamic", dyn), ("music", mus), ("movie", mov), ("voice", voi)):
        print(f"  {label:8s} " + " ".join(f"{v:+6.1f}" for v in c))
    # makeup：每档实测宽带响度增益（DAX2 ON/OFF RMS 差）
    build("Dolby2-Dynamic", dyn, rms_gain_db("loopback_pink_dynamic.wav"), root, dry)
    build("Dolby2-Movie",   mov, rms_gain_db("loopback_pink_movie.wav"),   root, dry)
    build("Dolby2-Music",   mus, rms_gain_db("loopback_pink_music.wav"),   root, dry)
    build("Dolby2-Voice",   voi, rms_gain_db("loopback_pink_voice.wav"),   root, dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
