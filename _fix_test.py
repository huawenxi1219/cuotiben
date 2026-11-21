# -*- coding: utf-8 -*-
import io
p = r'C:\myapp\_gen_band_test.py'
s = io.open(p, encoding='utf-8').read()
s = s.replace("const sleep = (ms) => new Promise(r => setTimeout(r, ms));",
              "Object.assign(PAGE, PAGE.private || {});   // 模拟框架把 private 映射到实例\nconst sleep = (ms) => new Promise(r => setTimeout(r, ms));")
s = s.replace("check('本次已背 5 个', PAGE.sessionCount === 5, PAGE.sessionCount);",
              "check('本次已显示第 6 个词', PAGE.sessionCount === 6, PAGE.sessionCount);")
s = s.replace("check('新词不在已学集合里', !DB.map[PAGE.curWord.i], PAGE.curWord.i);",
              "check('新词不在已学集合里', !(DB.map || {})[PAGE.curWord.i], PAGE.curWord.i);")
io.open(p, 'w', encoding='utf-8').write(s)
print('test harness updated')
