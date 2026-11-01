#!/bin/bash
# 切换 Dolby2 档位:  ~/bin-dolby.sh [dynamic|movie|music|voice|status]
ee_status() {
  flatpak run --command=sh com.github.wwmm.easyeffects -c "
python3 - <<'PY'
import socket,time
s=socket.socket(socket.AF_UNIX); s.settimeout(3)
s.connect('/tmp/EasyEffectsServer')
s.sendall(b'get_last_loaded_preset:output\n')
time.sleep(0.8)
try: print(s.recv(200).decode().strip())
except Exception: print('')
PY" 2>/dev/null | tail -1
}
P="${1:-status}"
case "$P" in
  dynamic|movie|music|voice)
    NAME="Dolby2-$(echo ${P:0:1} | tr a-z A-Z)${P:1}"
    J="$HOME/.var/app/com.github.wwmm.easyeffects/data/easyeffects/output/$NAME.json"
    [ -f "$J" ] || { echo "预设不存在: $J"; exit 1; }
    flatpak run com.github.wwmm.easyeffects -l "$NAME" >/dev/null 2>&1
    for i in 1 2 3 4 5; do
      sleep 1
      [ "$(ee_status)" = "$NAME" ] && { echo "已切换: $NAME ✓"; exit 0; }
    done
    echo "切换未确认（EE 报告: $(ee_status)）"
    ;;
  status) echo "当前生效档: $(ee_status)" ;;
  *) echo "用法: $0 [dynamic|movie|music|voice|status]"; exit 1 ;;
esac
