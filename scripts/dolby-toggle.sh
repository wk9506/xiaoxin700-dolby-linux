#!/bin/bash
# 用法: ~/bin-toggle-dolby.sh  —— 在 Dolby 校正 与 直通 之间切换（旁通全局链）
B=$(flatpak run com.github.wwmm.easyeffects -b 3)
if [ "$B" = "2" ]; then flatpak run com.github.wwmm.easyeffects -b 1; echo "Dolby2 效果: 旁通 OFF（=Linux 原声）"; else flatpak run com.github.wwmm.easyeffects -b 2; echo "Dolby2 效果: 已启用"; fi
