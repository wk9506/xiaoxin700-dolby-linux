import mmap, re, sys, time
P = '/media/k/327731E1CDAEF1C7/xiaoxin700.vhdx'
pats = [re.compile(p) for p in (
    rb'audio-optimizer-bands',                      # DAX3 XML utf-8/utf-16le 均可能
    rb'a\x00u\x00d\x00i\x00o\x00-\x00o\x00p\x00t\x00i',  # utf-16le 前缀
    rb'DEV_0235_SUBSYS',
    rb'\x00D\x00E\x00V\x00_\x000\x002\x003\x005',
)]
f = open(P, 'rb')
mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
t0 = time.time()
hits = [0]*len(pats)
CH = 1 << 24  # 16MB chunks
off = 0
n = mm.size()
step = max(n // 40, CH)  # 抽样进度打印
for i, pos in enumerate(range(0, n, CH)):
    b = mm[pos:pos+CH]
    for j, p in enumerate(pats):
        for m in p.finditer(b):
            hits[j] += 1
            if hits[j] <= 3:
                a = pos + m.start()
                print(f'HIT pat{j} @ {a} ({a/2**30:.2f} GiB)', flush=True)
    done = pos + CH
    if done % (1 << 30) < CH:
        print(f'... {done/2**30:.0f} GiB, {time.time()-t0:.0f}s, hits={hits}', flush=True)
print('DONE size=%d hits=%s elapsed=%.0fs' % (n, hits, time.time()-t0), flush=True)
