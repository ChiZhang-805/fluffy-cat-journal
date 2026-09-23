# v16 · 字段契约、陪伴语气与书写跳过

基线：`3b4612efba1a0e19d5f042debbf913bb7cb99917`（v15）。这是可运行代码修改，不是绘图。保留现有角色原图、动画骨架、首页、图表、照片单列输入、笔记有限滚动和中英文布局。

## 1. 每个字段的语义

`journal-guidance.js`为六类共25个字段提供含义、允许来源和排除项；类型、单位、必填、枚举、长度仍从`catalog.js`读取，避免维护两份冲突schema。每次只发送当前类别说明。

- 运动：项目是实际活动；分钟是本次时长；距离、组数、重量、感受在备注，不生成未说过的好心情。
- 饮食：餐次由用户给出；食用份量与整盘份量区分；kcal/g为本次总量；未知用null而不是0。图像不能生成用户备注。
- 情绪：自由混合感受、本人事件、本人想留的话；不生成强度分或替用户写励志句。
- 睡眠：同段睡眠两个24小时制时分；醒来感受来自用户；夜醒等补充放备注。不从时长推断感觉或疾病。
- 面部：自己的感受只来自自述；图像仅填可见眼周/皮肤外观；程序丢弃图像模型擅自返回的feeling和notes。
- 专注：新增解释预计时间，补记/修改解释实际时间；估时是单独用户主动入口，不能当任务已完成。

JSON示例已经改为合法空结构，不用`{...}`这样的省略号当示例。字段整理仍校验类型、范围、终止原因、空正文、对象结构与禁止键。回顾聊天仍是自然语言流式正文，不要求JSON或gesture数组。

## 2. 追问与修改保护

请求附带最小白名单`current`、`operation`、`missing`、已显示`lastQuestion`、有界同类候选摘要。小猫问时长后，用户回答“半小时”能获得正确字段上下文；不会发送Key、其他板块内容或原图到语言请求。

AI只返回本轮补丁。未提及不表示删除；明确清空还需原话匹配指定字段。若同时返回清空和新值，新值优先。用户等待期间修改的字段，以字段版本保护。

模型可以返回一个已知字段的缺项/歧义建议，前端用受控中英文短句表达；只对必须项或真实歧义追问。可选项空白不反复逼问。用户表示不想回答时，近期会话保留这个意愿；换页后清除短期问题上下文。

新的语音/文字整理不再在字段提取后串行等待第二个意图模型。明确入口和本地线索优先，同一次字段响应可提供附加意图建议；冲突进入显式确认，不自动新增/修改。回顾页的辅助意图判断保留独立任务，不阻塞聊天。

## 3. 陪伴语气

`companion-policy.js`补充六类主题边界、鼓励落点、最多一个必要追问、拒绝追问、已问过的问题、抱怨/辱骂和严重危险情境。

温柔、略可爱，不每句卖萌，不无依据奉承，不否定难过或疲惫。用户指出错误时承认具体问题、简短道歉、提供核对方向；没有证据时不编造错误原因，不假装已修好。被骂不回骂、不装委屈、不要求用户照顾AI感受。用户让它停就减少输出、不追问。出现明确紧急危险时减少卖萌，关注即时安全和现实支持。

这些是实际发送给DeepSeek的规则，不是模型准确率的证明。16个中文可见字符、1–2行、打断、实际显示才进入记忆等仍由v15代码控制。模型输出的语义与语气需要真实模型人工评测；不能以提示词存在代替评测。

## 4. 等待与生命周期

- 浏览器听写`stop()`后，已有最终文本且无尾句时等待约180ms稳定窗口即可完成；仍有临时尾句时等待识别结束，兜底2200ms。松手关闭麦克风；取消使用abort清理旧回调。
- 一次记录整理默认30秒总预算，涵盖主请求；超时保留原话，点击小猫显式重试。它是上限，不是正常耗时目标或承诺。
- 无歧义的睡眠时段可先填待确认草稿，其余内容继续整理；手工修改仍优先。
- 隐藏页面时停止收音和摄像头；已经提交的整理不因为标签页隐藏就直接取消。浏览器/系统仍可能挂起或终止网页；实际失败要重新恢复，不能保证后台常驻。
- 真正取消时，按钮、阶段、动画和气泡一起结束思考。导航、换日期、修改Key等会使迟到响应无效。
- `workflow-trace.js`只保留32次请求的有界阶段与毫秒、类别、故障码，不含原文、字段值、Key、图像、录音。`FluffyWorkflowDiagnostics.snapshot()`可供开发检查。回顾聊天仍用`FluffyChatDiagnostics.snapshot()`。

估时另检查任务、目标描述、时长三个字段的版本，避免任务已改但旧预计时间仍回填。翻译仍保留原文，只维护内存阅读副本；旧的百炼原始音频评测入口改为DeepSeek文字评测，防止工具与实际APP路由相反。

## 5. 书写页两秒门闩

`continue-gate.js`用`performance.now()`计时，独立于动画帧和系统时钟。页面切入重置，两秒后才接受新的有效点击。

- 0–1999ms：点击静默丢弃，不存排队事件，不显示防误触说明或倒计时。
- 两秒前按下、两秒后松开：仍忽略；需新的有效按下。
- 满两秒：可跳过剩余书写/放笔/趴睡，但不跳过录入确认或专注计时。
- 以进入笔记前确认的完整快照保存，未画出的营养等字段也必须保存。
- 门闩原子锁定，重复触摸/点击不会重复存储。保存失败解锁，留在笔记页由小猫说明。
- 可访问性状态用独立定时同步；暂停绘制时也按真实两秒开放，不出现“时限已过但按钮仍不可用”。

不点击时，原有完整循环书写、准确归位、有限上下滚动继续正常运行。

## 6. 审查范围与有意保留

修改/检查的主要生产链路：`catalog/model/entry-action` → `journal-guidance/ai-journal/ai-policy` → `speech/microphone/gesture` → `app` → `animation/notebook-layout/continue-gate` → `journal-store/review-data` → `review/review-conversation/companion-policy/chat-stream/chat-text/chat-memory`。

另检查照片草稿所有权、换图取消、百炼地址限制、DeepSeek Key代次、显示翻译、睡眠日期、专注实际计时、所有脚本语法、索引资源顺序、打包资源与更新清单。

没有为“收尾”而重写稳定的角色动画、评分计算、历史兼容和照片模块。`audio-session.js`保留为历史兼容资料，不再从网页索引加载；不能据它的存在声称当前进行了音色情绪分析。`docs/v5...v15`及旧研究文档是历史记录，当前路由以本文件和README为准。

## 7. 可重复执行的测试

```sh
npm test
python tests/refinement_v16_browser.py
python tests/chat_v15_browser.py
python tests/notebook_v14_browser.py
python tests/v13-browser.py
python tools/audit-comments.py
python tools/build-standalone.py ../Fluffy-Cat-v16.html
```

Node测试使用生产模块和隔离环境。浏览器测试渲染生产HTML/CSS/JS及原角色素材；API、听写、麦克风权限、摄像头流和存储使用明确的测试替身，不是真人设备或真实模型识别。六类表单/回顾、已有记录修改、后台恢复、手动覆盖保护、连点/长按跨边界、暂停动画、保存失败和完整数据保存均有专门断言。

真实AI评测工具提供39个人工合成场景，默认dry-run绝不联网：

```sh
node tools/evaluate-ai.cjs --limit=39
# 下列命令只有本机已设置DEEPSEEK_API_KEY才执行，且会产生真实API费用：
node tools/evaluate-ai.cjs --allow-api --limit=6 --out=ai-evaluation.local.json
node tools/evaluate-ai.cjs --allow-api --id=chat-insult --limit=1
```

不把Key写入命令行或文件。工具调用当前生产客户端、提示词和解析；报告保留人工复核位与实际耗时，不生成虚假的“准确率”。旧`npm run evaluate:emotion`现指向该工具的情绪文字用例，不发送原始音频到百炼。

**本次没有真实Key，真实AI评测仅执行dry-run；未实测真人麦克风/摄像头、付费模型、iPhone/Safari、Windows上线更新。** 因此不能宣称所有真实场景均正确或外部服务永不失败。`verification`里分别保存实际自动化结果、脚本检查、dry-run与未执行边界。

## 8. 更新与回滚边界

外层`Update-GitHub-Pages.cmd`只针对已存在的仓库。对比本地文件SHA、远程基线和相关依赖后，以一次提交更新；非强制推进main，未知改动停止，不删除无关文件。网站继续用原Pages配置。GitHub写入本次返回403，未创建分支或提交；提供更新包不等于线上已更新。

用户数据在浏览器本地，不在更新包。不要清理网站存储当作更新步骤。故障可以使用GitHub提交历史恢复代码，但那与恢复浏览器数据是不同事项。

## 核对的官方接口资料

- DeepSeek JSON Output：`https://api-docs.deepseek.com/guides/json_mode/`（说明空内容仍可能发生；本地校验不可省略）。
- DeepSeek Chat Completions：`https://api-docs.deepseek.com/api/create-chat-completion/`（显式关闭thinking，流式用于陪伴正文）。
- SpeechRecognition.stop：`https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/stop`（结束识别并尝试返回已有结果，不等于abort）。
- performance.now：`https://developer.mozilla.org/en-US/docs/Web/API/Performance/now`（交互门闩使用单调计时）。

核对日期：2026-09-23。没有引入新的生产依赖、外部字体或不同AI供应商。
