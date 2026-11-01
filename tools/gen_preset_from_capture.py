#!/usr/bin/env python3
"""XiaoXin 700-15ISK: 从 Windows Dolby(DAX2) 实测数据生成 EasyEffects 8 预设。

数据源：captures/loopback_pink_{off,dynamic,voice}.wav（WASAPI loopback 电域稳态）
曲线 = dynamic−off 的 20 带 PSD 差（= audio-optimizer 校正 + IEQ voicing 的合成，
与项目 DAX3 convolver 的输入同构）。L=R 差为 0，单 FIR 双声道共用。

复用 speaker-tuning-to-easyeffects 的 lib（make_fir 最小相位、make_convolver、
make_limiter、save_wav_stereo、kernel_name），零新增 DSP 假设。
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


def build(name: str, gains_db: list[float], safety_db: float,
          out_root: Path, dry: bool = False) -> dict:
    freqs = np.array(BANDS, dtype=float)
    taps, peak_db = fir.make_fir(freqs, np.array(gains_db))
    # make_fir 把曲线整体压低了 peak_db（峰归一）。Windows 实测 Dolby 输出
    # 峰值 −0.11 dBFS（顶到满幅由它自己的限幅器兜底），所以忠实还原 = 把
    # peak_db 全部补回，只留 safety_db 的余量给 limiter#0 做 brickwall。
    makeup_db = peak_db - safety_db
    stem = kernel_name(name, stereo_taps(taps, taps))
    irs = out_root / "irs" / f"{stem}.irs"
    preset = {
        "_generator": {"tool": "dax_measure/gen_xiaoxin_preset.py",
                       "source": "Windows WASAPI loopback, XiaoXin 700-15ISK DAX2",
                       "note": f"curve peak {peak_db:+.1f} dB, makeup {makeup_db:+.1f} dB"},
        "output": {
            "blocklist": [],
            "convolver#0": make_convolver(stem),
            "limiter#0": make_limiter(input_gain=makeup_db),
            "plugins_order": ["convolver#0", "limiter#0"],
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
    # safety_db：留给 brickwall 的余量。Windows 实测 Dolby 顶到 −0.1 dBFS，
    # 我们用 −1 dB（limiter 阈值）起步；听感太保守可降到 0.5。
    build("Dolby2-Dynamic", dyn, 1.0, root, dry)
    build("Dolby2-Movie", mov, 1.0, root, dry)
    build("Dolby2-Music", mus, 1.0, root, dry)
    build("Dolby2-Voice", voi, 1.5, root, dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
