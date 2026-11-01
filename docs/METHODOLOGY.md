# 测量方法与数据

## 设备

- Lenovo XiaoXin 700-15ISK（机型码 80SH，Skylake）
- 声卡 Realtek ALC235（codec `0x10EC0235`，子系统 `0x17AA3831`），2 扬声器立体声
- Windows 10 Enterprise 19045（VHDX，经 Ventoy vhdboot 引导实测）
- Dolby Audio（DAX2 桌面应用架构；`HKLM\SOFTWARE\Dolby\DAX`，参数存于
  加密 `DAX2.sdf`，无明文 DAX3 XML）

## 为什么走黑盒测量

上游项目需要 DAX3 XML，本机不存在；DAX2 参数在加密库里。
但 EasyEffects 预设真正需要的不是参数，而是 **Dolby 对音频的净变换**。
WASAPI loopback 录的是"经过全部 APO 处理、送到端点前"的信号，
ON/OFF 两组一除，净变换即得——无需解密。

## 采集（tools/windows-capture/）

刺激：上游 `make_stimulus.py` 标准套件（48 kHz float32，L=R）

| 刺激 | 电平 | 用途 |
|---|---|---|
| stimulus_sweep | −18 dBFS peak | 反卷积求 IR（LTI 假设检验） |
| stimulus_sweep_quiet | −42 dBFS peak | 电平相关性 |
| stimulus_pink / _quiet | −18 / −42 dBFS RMS | 稳态 PSD 差（主曲线来源） |
| stimulus_multitone | −18 dBFS RMS | 20 带逐带幅度（交叉验证） |

标签：`off`（系统"禁用所有声音效果"）+ `dynamic/movie/music/voice`
（Dolby Audio 对应页）。16 条，全部零削波，48 kHz。

"Dolby 关"的实现说明：本机 DAX2 UI 无总开关，用 Windows 端点级
"禁用所有声音效果"移除 APO 链；OFF 捕获的电平/频谱与刺激完全一致
（sweep_off 峰值 −17.99 vs 刺激 −18.00 dBFS），证明基线干净。

## 分析结果

### 净 EQ（pink 稳态 PSD 差，dynamic−off，20 带，dB）

```
  47   141   234   328   469   656   844  1031  1313  1688
 -5.7 +14.8 +15.5 +14.4  +8.2  -1.5  -1.4  +5.7  +5.6  +6.7
 2250  3000  3750  4688  5813  7125  9000 11250 13875 19688
+11.7  +8.7  +9.1  +7.8  +9.2  +4.6 +12.0 +15.9 +15.7  +4.2
```

L=R 完全对称（差 0.00 dB）。

### 交叉验证

- 扫频反卷积 IR 的频响比 vs 粉噪 PSD 差：形状一致，绝对值差 ≤2 dB
  （粉噪含限幅器的稳态压缩，扫频含瞬态，属预期）；
- multitone 逐带幅度：47 Hz 相对 141 Hz 的 −20.5 dB 在两套独立数据中吻合；
- 四档曲线单调有序：Music ≥ Dynamic ≈ Movie > Voice，与 UI 定位一致。

### 电平器证据（未复刻，见 README 限制）

−42 dBFS 输入时 Dolby 净推 ≈ +20 dB，−18 dBFS 时 ≈ +8.4 dB：
输入每低 1 dB 输出约补 1 dB，典型的 volume leveler。

### 限幅行为

ON 捕获峰值 −0.11 dBFS（四档、五刺激全部如此）：Dolby 把输出顶到满幅
由自身 limiter 控制。预设因此以"补回 FIR 归一化损失 −1 dB 余量 + brickwall"
复刻其响度与保护。

## 生成

`tools/gen_preset_from_capture.py`（依赖上游仓库的 `lib/preset/`）：

1. 从 captures 提取 20 带差值曲线；
2. 上游 `make_fir`：cepstral 同态处理 → 4096 抽头最小相位 FIR（零附加延迟，
   拟合误差 0.00 dB）；
3. 预设 = convolver（引用 .irs）+ limiter（−1 dBFS, Herm Thin, ALR on）；
4. makeup = FIR 峰值归一损失 + 安全余量（Dynamic/Movie/Music 1.0 dB，Voice 1.5 dB）。

## 数据文件

`captures/` 原始 16 条 wav（约 90 MB）未入库（GitHub 限制与体积考虑），
采集方可用 `tools/windows-capture/` 复现。分析中间产物：

- `dyn_off_curve.npy`：20 带差值矩阵（本文档表格的来源）
