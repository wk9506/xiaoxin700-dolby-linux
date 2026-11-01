#!/usr/bin/env bash
# 一键安装 Dolby2 预设到 EasyEffects 8（原生或 Flatpak 均可）
# 用法: bash scripts/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."

install_to() {
  local root="$1" label="$2"
  mkdir -p "$root/output" "$root/irs" "$root/autoload/output"
  cp -v "$PWD/presets"/*.json "$root/output/"
  cp -v "$PWD/irs"/*.irs "$root/irs/"
  echo "  -> $label: $root"
}

echo "== XiaoXin 700-15ISK Dolby 预设安装 =="
found=0
if command -v flatpak >/dev/null 2>&1 && flatpak info com.github.wwmm.easyeffects >/dev/null 2>&1; then
  install_to "$HOME/.var/app/com.github.wwmm.easyeffects/data/easyeffects" "Flatpak EasyEffects"
  found=1
fi
if [ -d "$HOME/.local/share/easyeffects" ] || command -v easyeffects >/dev/null 2>&1; then
  install_to "$HOME/.local/share/easyeffects" "原生 EasyEffects"
  found=1
fi
if [ "$found" = 0 ]; then
  echo "未检测到 EasyEffects 8。请先安装：" >&2
  echo "  flatpak install flathub com.github.wwmm.easyeffects" >&2
  exit 1
fi

# autoload：内置扬声器一出现就自动加载 Dynamic 档。
# EasyEffects 的 autoload 文件名是 {sink节点名}:{激活输出route描述}.json，
# route 描述跟随系统语言（中文系统=“扬声器”），所以这里动态探测。
python3 - <<'PY' || echo "（autoload 未能自动配置：可在 EasyEffects 窗口里手动为扬声器选 preset）"
import json, os, subprocess, sys
try:
    d = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True).stdout)
except Exception as e:
    sys.exit(f"pw-dump 失败: {e}")
# Device id -> {card.profile.device -> 输出 route 描述}（EasyEffects autoload 匹配用）
routes = {}
for obj in d:
    if not str(obj.get("type", "")).endswith("Device"):
        continue
    params = obj.get("info", {}).get("params", {})
    out = {}
    for r in (params.get("Route") or []) if isinstance(params, dict) else []:
        if r.get("direction") == "Output" and r.get("device") is not None and r.get("description"):
            out[r["device"]] = r["description"]
    if out:
        routes[obj["id"]] = out
sink = None
for obj in d:
    props = obj.get("info", {}).get("props", {})
    if isinstance(props, dict) and props.get("media.class") == "Audio/Sink" \
            and str(props.get("node.name", "")).startswith("alsa_output"):
        sink = props
        break
if not sink:
    sys.exit("没找到 alsa_output sink（内置扬声器）")
route = routes.get(sink.get("device.id"), {}).get(sink.get("card.profile.device"))
if not route:
    sys.exit("没找到输出 route 描述")
node = sink["node.name"]
for root in [os.path.expanduser("~/.var/app/com.github.wwmm.easyeffects/data/easyeffects"),
             os.path.expanduser("~/.local/share/easyeffects")]:
    if not os.path.isdir(root):
        continue
    ad = f"{root}/autoload/output"
    os.makedirs(ad, exist_ok=True)
    safe = node.replace("/", "_") + ":" + route.replace("/", "_")
    with open(f"{ad}/{safe}.json", "w") as f:
        json.dump({"device": node, "device-description": sink.get("node.description", ""),
                   "device-profile": route, "preset-name": "Dolby2-Dynamic"},
                  f, ensure_ascii=False, indent=4)
    print(f"  autoload: {safe}.json -> Dolby2-Dynamic")
PY

echo
echo "完成。下一步："
echo "  1) 启动 EasyEffects（托盘图标或 systemctl --user start easyeffects）"
echo "  2) 把系统默认输出选为 'Easy Effects Sink'（GNOME 音量菜单）"
echo "  3) 换档:  bash scripts/dolby-switch.sh movie"
echo "  4) 体检:  bash scripts/dolby-check.sh"
