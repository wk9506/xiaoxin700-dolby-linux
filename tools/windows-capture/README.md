# Windows 端测量工具包

在任何"有 Windows + Dolby 但拿不到明文调音 XML"的机器上复现本项目的测量。
（本仓库的预设就是用这套工具在小新 700 上测出来的。）

## 文件

| 文件 | 作用 |
|---|---|
| `capture_dax.py` | 播放刺激 + 录 WASAPI loopback（上游 measure_dax 工具，MIT） |
| `make_stimulus.py` | 生成刺激套件（上游） |
| `analyze.py` | Linux 端反卷积/PSD 分析（上游，需上游仓库的 `lib/`） |
| `stimulus/` | 预生成好的 5 条核心刺激（wav + json sidecar + inverse_sweep.npy），免装 Python 直接可用 |
| `setup.cmd` | Windows 端一键装便携 Python + 离线依赖（自带 wheels 见下方"离线打包"） |
| `run_probe.cmd` | 单条探针：验证 播放→录音 链路 |
| `run_capture_off.cmd` | 录 OFF 基线（5 条） |
| `run_capture_dolby.cmd` | 录 Dolby ON 档（5 条） |
| `CHECKLIST_zh.txt` | 中文操作清单（含 Ventoy/VHDX 引导、Dolby 开关位置等实战细节） |

## 快速流程

```
Windows:
  1. 系统声音设置里对扬声器勾选"禁用所有声音效果"（或等效的 APO 移除）
  2. run_probe.cmd → 确认录出 stim\captures\loopback_pink_off.wav
  3. run_capture_off.cmd            （OFF 基线）
  4. 打开 Dolby（选目标档，如 Dynamic），再 run_capture_dolby.cmd
  5. 换档重复第 4 步（movie/music/voice 各一次，改 --label）
Linux:
  6. 把 captures\ 拷回，跑 tools/gen_preset_from_capture.py
```

## 离线打包（无外网 Windows）

`setup.cmd` 需要以下文件放在同目录 `py\` 下（本仓库不含，自行下载）：

- `py/python-embed.zip` ← python.org 的 3.12 embeddable amd64
- `py/get-pip.py` ← bootstrap.pypa.io
- `py/wheels/` ← 在 Linux 上执行：
  ```bash
  pip download --dest wheels --platform win_amd64 --python-version 312 \
    --only-binary=:all: --implementation cp \
    numpy scipy soundfile sounddevice pycaw comtypes pyaudiowpatch pip
  ```

embeddable Python 的 `._pth` 陷阱已在 `setup.cmd` 里处理（写入
`Lib\site-packages` + `import site`），否则 pip 装了也 import 不到。

## 常见坑（都踩过）

- **cmd 脚本必须纯 ASCII**：UTF-8 中文注释在 GBK 码页下会把命令行切碎
  （"'t' 不是内部或外部命令"）；
- **刺激文件带 `.json` sidecar**，`capture_dax.py` 靠它校验 sha256 和分析窗口，
  不能只拷 wav；
- **OFF 基线必须先录**：脚本用它做"忘切档"相似度检查；
- 全程内置扬声器、同一系统音量、48 kHz（脚本会校验端点格式）。
