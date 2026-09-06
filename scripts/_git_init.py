# -*- coding: utf-8 -*-
"""重建 .git：fresh init -> 提交当前快照 -> force push
（旧 .git 已删除，完整备份在 D:\\备份\\.git-obsidian-20260906）
"""
import os, subprocess

R = r"D:\My knowledge vault"
REMOTE = "git@github.com:JXSWR/obsidian-notes.git"

def g(*a, check=True):
    r = subprocess.run(['git'] + list(a), cwd=R, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"  ✗ git {' '.join(a[:3])} 失败 rc={r.returncode}")
        print(f"    stderr: {r.stderr[-400:]}")
    return r

print("=== 1. git init ===")
print(g('init', '-b', 'master').stdout.strip()[-160:])
print("  分支:", g('rev-parse', '--abbrev-ref', 'HEAD').stdout.strip())

print()
print("=== 2. 暂存 ===")
g('add', '-A')
st = [x for x in g('status', '--porcelain').stdout.splitlines() if x.strip()]
print(f"  暂存条目: {len(st)}")

names = [x for x in g('diff', '--cached', '--name-only', '-z').stdout.split('\0') if x.strip()]
tot = 0
big = []
for nm in names:
    p = os.path.join(R, nm)
    if os.path.isfile(p):
        s = os.path.getsize(p)
        tot += s
        if s > 1024 * 1024:
            big.append((s, nm))
print(f"  暂存体积: {tot/1024/1024:.2f} MB / {len(names)} 项")
if big:
    print("  ★ >=1MB:")
    for s, nm in sorted(big, reverse=True):
        print(f"      {s/1024/1024:.2f} MB  {nm}")
else:
    print("  无 >=1MB 文件 ✓")

print()
print("=== 3. 提交 ===")
msg = ("重建仓库：剔除历史 3D 文件包袱（424 MB -> 轻量），仅保留当前快照\n\n"
       "历史包袱来源：05_项目案例库 831 个 3D 文件（SLDPRT/SLDASM/SLDDRW/STEP）\n"
       "曾入库后删除，git 对象仍留在 .git 中，致其膨胀至 424 MB。\n\n"
       "旧历史完整备份：D:\\备份\\.git-obsidian-20260906（332 文件 / 424.04 MB，校验通过）。\n"
       "如需回溯旧提交，用备份目录替换 .git 即可。")
r = g('commit', '-m', msg)
print("  ", r.stdout.strip().splitlines()[0] if r.stdout else r.stderr[-200:])

print()
print("=== 4. 远程 ===")
g('remote', 'remove', 'origin', check=False)
g('remote', 'add', 'origin', REMOTE)
print("  ", g('remote', '-v').stdout.strip().splitlines()[0] if g('remote','-v').stdout.strip() else "(无)")

print()
print("=== 5. force push ===")
r = g('-c', 'gc.auto=0', 'push', '--force', 'origin', 'master', check=False)
print("  rc:", r.returncode)
if r.stdout.strip(): print("  stdout:", r.stdout.strip()[-250:])
if r.stderr.strip(): print("  stderr:", r.stderr.strip()[-250:])

print()
print("=== 6. 验证 ===")
def q(*a): return g(*a, check=False).stdout.strip()
print("  本地 HEAD:", q('rev-parse', '--short', 'HEAD'))
print("  远程 HEAD:", q('rev-parse', '--short', 'origin/master'))
print("  ahead/behind:", q('rev-list', '--left-right', '--count', 'origin/master...master'))
print("  工作区:", "干净" if not q('status', '--porcelain') else "有未提交")
print("  跟踪文件:", len(q('ls-files').splitlines()))
print("  提交数:", q('rev-list', '--count', 'HEAD'))
gb = 0
for dp, dn, fn in os.walk(os.path.join(R, '.git')):
    for f in fn:
        try: gb += os.path.getsize(os.path.join(dp, f))
        except OSError: pass
print(f"  .git 体积: {gb/1024/1024:.2f} MB  (原 424.04 MB)")
