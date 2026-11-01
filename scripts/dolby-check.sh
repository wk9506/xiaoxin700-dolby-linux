#!/bin/bash
# 体检：声音到底有没有经过 Dolby 链
echo "1) EE 服务: $(systemctl --user is-active easyeffects 2>&1)"
DEF=$(wpctl status 2>/dev/null | grep -A3 'Default Configured' | grep 'Audio/Sink' | awk '{print $NF}')
echo "2) 默认输出: ${DEF:-?}"
if [ "$DEF" = "easyeffects_sink" ]; then echo "   ✓ 走 Dolby 链"; else
  EID=$(pw-dump | python3 -c "
import json,sys
d=json.load(sys.stdin)
for n in d:
    if '\"node.name\": \"easyeffects_sink\"' in json.dumps(n): print(n['id']); break" 2>/dev/null)
  echo "   ✗ 没走链！自动修复中…"; [ -n "$EID" ] && wpctl set-default $EID && echo "   已修复 (id=$EID)"
fi
grep -q ee_soe_convolver <(pw-dump 2>/dev/null) && echo "3) 链上 convolver: ✓ 在跑" || echo "3) 链上 convolver: （无播放时未创建，正常）"
echo "4) kernel: $(grep kernelName ~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/db/convolverrc 2>/dev/null | cut -d= -f2 || echo 未加载)"
IDS=$(pw-dump 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
alsa=ee=None
for n in d:
    s=json.dumps(n)
    if '\"node.name\": \"alsa_output' in s and '\"Audio/Sink\"' in s: alsa=n['id']
    if '\"node.name\": \"easyeffects_sink\"' in s: ee=n['id']
print(alsa or '?', ee or '?')")
read -r ALSA EE <<<"$IDS"
echo "5) 音量: 硬件(id $ALSA)=$(wpctl get-volume $ALSA 2>/dev/null | awk '{print $2}')  EE链(id $EE)=$(wpctl get-volume $EE 2>/dev/null | awk '{print $2}')"
echo "   （日常调音量拖桌面音量条即可；硬件层建议保持 0.55）"
