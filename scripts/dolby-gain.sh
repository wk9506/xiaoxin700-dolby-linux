#!/bin/bash
# 用法: ~/bin-dolby-gain.sh <dB>   例: ~/bin-dolby-gain.sh 8
# 三件套总响度旋钮: 卷积曲线不变, 压缩器 makeup = G+6, 限制器 makeup = G-3
# 改完后必须在 EasyEffects 界面重新点一下当前预设才生效！
G="${1:?用法: $0 <dB>}"
python3 - "$G" <<'PY'
import json,os,sys
g=float(sys.argv[1])
base=os.path.expanduser('~/.var/app/com.github.wwmm.easyeffects/data/easyeffects/output')
for n in ['Dolby2-Dynamic','Dolby2-Movie','Dolby2-Music','Dolby2-Voice']:
    p=f'{base}/{n}.json'
    d=json.load(open(p)); out=d['output']
    out['compressor#0']['makeup']=g+6
    out['limiter#0']['input-gain']=g-3
    json.dump(d,open(p,'w'),indent=4,ensure_ascii=False)
print(f'✓ 压缩器 makeup = {g+6} dB, 限制器 makeup = {g-3} dB')
PY
echo '→ 到 EasyEffects 界面重新点一下当前预设生效'
