# -*- coding: utf-8 -*-
"""验证词库分页加载逻辑：offset/BATCH 边界与加载更多按钮出现条件"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def simulate(total, BATCH=100, pages=None):
    offset = 0
    out = []
    while True:
        shown = min(offset + BATCH, total)
        if total > BATCH:
            out.append((offset, shown, shown < total, f"还剩{total - shown}词"))
        else:
            out.append((offset, shown, False, "单页"))
        if shown >= total:
            break
        offset += BATCH
        if pages is not None and len(out) >= pages:
            break
    return out

ok = True
# 1) 词库全量 4678
r = simulate(4678)
check1 = r[-1][1] == 4678 and len(r) == 47  # ceil(4678/100)=47
ok &= check1
print("词库4678词:", "47页全覆盖" if check1 else "FAIL", f"最后页{len(r)}次加载到{r[-1][1]}")

# 2) 搜索过滤后 150 词
r2 = simulate(150)
ok &= (r2[0][0] == 0 and r2[0][1] == 100 and r2[0][2] == True
       and r2[1][0] == 100 and r2[1][1] == 150 and r2[1][2] == False)
print("150词: 2页(100+50) 加载更多按钮在第1页出现:", r2)

# 3) 单页边界 100
r3 = simulate(100)
ok &= (len(r3) == 1 and r3[0][2] == False)
print("100词: 单页无按钮:", r3)

# 4) 0 词（空搜索结果）
r4 = simulate(0)
print("0词: ", r4)

print("分页逻辑:", "通过" if ok else "FAIL")
sys.exit(0 if ok else 1)
