# XiaoXin 700 Dolby → Linux 扬声器音效移植

把 **联想小新 700-15ISK**（2016，Skylake，Realtek ALC235/ALC233）Windows 里
Dolby Audio（DAX2）的扬声器音效，用**黑盒声学测量**的方法移植到 Linux
（PipeWire + EasyEffects 8）。

效果：音量恢复到接近 Windows（+8 dB 级别）、低频更扎实、大音量不破音。

> 本机没有 DAX3 调音 XML（2016 机型用 DAX2，参数锁在加密的 `dax2.sdf` 里），
> 因此无法直接用 [speaker-tuning-to-easyeffects](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects)
> 转换。本项目改用它的 `measure_dax` 测量工具链：**在 Windows 里录 Dolby 开/关
> 两组 loopback，反推出 Dolby 的净传输函数，生成最小相位 FIR**。
> 全程未逆向、未解密任何 Dolby 组件。

## 快速开始（Linux 端，5 分钟）

前提：PipeWire + EasyEffects **8.x**（Debian/Ubuntu apt 源多为 7.x，不兼容，用 Flatpak）：

```bash
flatpak install flathub com.github.wwmm.easyeffects
git clone https://github.com/wk9506/xiaoxin700-dolby-linux.git
cd xiaoxin700-dolby-linux
bash scripts/install.sh
```

然后：

1. 打开 EasyEffects（托盘图标），确认 Presets 里显示 `Dolby2-Dynamic`；
2. 系统音量菜单把输出设备选为 **Easy Effects Sink**；
3. 放音乐试听。换档：

```bash
bash scripts/dolby-switch.sh movie|music|voice|dynamic   # 四档切换
bash scripts/dolby-switch.sh status                      # 当前生效档
bash scripts/dolby-check.sh                              # 体检：声音是否真的走了链
bash scripts/dolby-toggle.sh                             # Dolby 效果 开/关 A/B 对比
```

## 四个预设（对应 Windows Dolby Audio 的档位）

| 预设 | Windows 档位 | 特点（实测，相对关闭 Dolby） |
|---|---|---|
| `Dolby2-Dynamic` | 动态 | 默认推荐。100–300 Hz +15 dB、2–6 kHz +9 dB、9–14 kHz +12~16 dB、47 Hz 以下保护性 −6 dB |
| `Dolby2-Movie` | 电影 | 与动态几乎相同（≤1.3 dB），低频保护略多 |
| `Dolby2-Music` | 音乐 | 最亮最响，总增益最高 |
| `Dolby2-Voice` | 语音 | 最收敛，656–844 Hz 凹陷最深（突出对白） |

每个预设 = Convolver（4096 抽头最小相位 FIR，零附加延迟）+ Limiter（−1 dBFS
brickwall + ALR，防破音）。

## 目录结构

```
presets/     EasyEffects 8 预设 JSON ×4
irs/         最小相位 FIR 冲激响应（RIFF float32 48kHz 4096 抽头）×4
scripts/     install.sh 安装 / dolby-switch.sh 换档 / dolby-check.sh 体检 / dolby-toggle.sh A-B
tools/
  gen_preset_from_capture.py   核心：loopback 采集 → 20 带差值曲线 → 最小相位 FIR → 预设
  vhdx_probe.py                （可选）VHDX 全盘扫描调音文件
  windows-capture/             Windows 端测量工具包（见其 README）
docs/        测量数据与结论
```

## 方法论（怎么测的、怎么生成的）

1. **采集**（Windows 端）：把 VHDX 虚拟磁盘经 Ventoy 引导进 Win10，用
   `capture_dax.py` 对 5 种标准刺激（指数扫频 ×2 电平、粉噪 ×2 电平、20 带多音）
   分别录 **Dolby 关**（系统"禁用所有声音效果"）与 **Dolby 开**（动态/电影/音乐/语音）
   的 WASAPI loopback，共 16 条，48 kHz float32，全部零削波。
2. **反推**（Linux 端）：
   - 扫频：反卷积出各档冲激响应，`ON/OFF` 频响比 = Dolby 净 EQ（SNR 86–108 dB）；
   - 粉噪：Welch PSD 差 = 稳态工作点曲线；
   - 多音：逐带 Goertzel 幅度 = 独立交叉验证。三者互相吻合。
3. **生成**：20 带差值曲线 → 项目上游的 cepstral 最小相位 FIR（拟合误差 <0.1 dB）
   → EasyEffects 预设 + limiter 兜底。

细节与原始数据见 [docs/METHODOLOGY.md](docs/METHODOLOGY.md)。

## 已知限制

- **静态曲线**：Dolby 的电平器（实测：−42 dBFS 轻信号被多推约 +11 dB）没有复刻。
  小声内容可能需要手动拧音量。要补的话：用 `tools/windows-capture/` 补录电平梯刺激
  （7 档 ×2，约 6 分钟），配 EasyEffects Autogain。
- **动态处理**：Dolby 的多段压缩/每段限幅用固定 brickwall limiter 近似。
- **48 kHz 假设**：PipeWire 图跑 >48 kHz 时 convolver 会重采样且不补增益（预设会偏响）。
  保持默认 48 kHz 即可。
- 曲线是小新 700-15ISK 这台机器的，**不适用于其他机型**（但工具链适用于任何
  "有 Windows + Dolby 但拿不到明文 XML"的机器）。

## 致谢与许可

- 测量与 FIR 生成方法复用 [antoinecellerier/speaker-tuning-to-easyeffects](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects)（MIT, © Antoine Cellerier）的 `lib/preset/fir.py`、`measure_dax` 工具链；
- 本项目自有内容（预设、脚本、文档）同样以 MIT 许可发布，见 [LICENSE](LICENSE)。
- Dolby 是 Dolby Laboratories 的商标；本项目与 Dolby/联想无隶属关系。
