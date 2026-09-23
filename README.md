# Fluffy Cat · v16 AI交互与完整记录

基于已发布v15的收尾修改。保留同一只小猫、六入口首页、双语、回顾聊天、照片自动分析、两秒后可继续的完整笔记、专注计时及已有数据。

## 本版修改

- 六类25个字段加入语义说明，类型/单位/范围仍从catalog读取。每次只发送当前类别的字段说明。
- 整理请求携带当前草稿、真实显示过的问题和操作类型。短答可接着填写；不把助手的鼓励写入用户备注。未提及不清空旧值，手动新修改优先。
- 小猫语气更偏向温柔具体的鼓励，有必要时最多一个追问；尊重不想回答，面对抱怨或辱骂不回击、不装委屈、不假装已经修好。
- 回顾聊天继续使用DeepSeek流式正文、16字符中文分页、可随时打断和仅记住实际显示的回复。
- 记录整理不再串行等待另一轮普通意图模型；无歧义睡眠时间可以先显示草稿。提交后的整理切后台不直接取消；实际取消后按钮与气泡同步恢复。
- 书写页显示两秒后，点击原来的“继续”即可跳过剩余动画；前两秒静默忽略、不显示倒计时。保存的是完整确认记录，不是已经画出的几行。重复点击不重复保存。暂停动画也按真实两秒开放。

## 运行

网站本身无npm运行依赖，放在GitHub Pages或本地静态服务器即可。

```sh
python -m http.server 8000
# 也可构建离线手动预览，联网能力仍需要有效Key/权限/网络：
python tools/build-standalone.py ../Fluffy-Cat-v16.html
```

浏览器语音听写不是DeepSeek的音频接口；语言处理固定DeepSeek，照片固定百炼。两份Key仅在当前页面私有内存；刷新需重新填写。正文、照片与录音不写入代码仓库。现在仍是浏览器本地记录，不是云同步APP。清理网站存储可能删除记录，删除下载包不会删除网站记录。

## 测试和真实模型评测

```sh
npm test
python tests/refinement_v16_browser.py
python tests/chat_v15_browser.py
python tests/notebook_v14_browser.py
python tests/v13-browser.py
python tests/standalone_v16.py ../Fluffy-Cat-v16.html
python tools/audit-comments.py
node tools/evaluate-ai.cjs --limit=39
```

本轮实际执行：**521项单元测试、349项浏览器/最终HTML断言、226处命名函数或方法注释检查**。54个生产JS文件语法检查通过，索引引用资源存在，原猫咪素材字节未改。详细报告放在外层`verification`，范围说明见`docs/v16-ai-readiness.md`。

浏览器测试渲染交付源码、真实DOM/Canvas和原角色素材，API、听写、权限、摄像头和存储按测试注明的边界隔离。不能把这些测试当作真人设备或真实模型识别准确率。

39个真实模型评测场景包含六类整理、缺项、半句话回答、纠错、否定、反讽、抱怨、拒绝追问、中英文和严重危险。默认dry-run不联网。维护者在本机设置`DEEPSEEK_API_KEY`后，可显式允许付费调用：

```sh
node tools/evaluate-ai.cjs --allow-api --limit=6 --out=ai-evaluation.local.json
```

报告使用生产提示词、客户端和校验，保存实际响应、耗时及人工判断位；不计算虚假准确率。**本次未持有实际Key，只执行了dry-run，未完成真实模型、真人麦克风/摄像头、iPhone/Safari和Windows在线更新实测。**

`FluffyWorkflowDiagnostics.snapshot()`和`FluffyChatDiagnostics.snapshot()`只给出不含原文/Key的有界阶段诊断。它们不是聊天导出，也不持久化用户内容。

## 更新当前GitHub网站

完整解压外层更新包，双击 **`Update-GitHub-Pages.cmd`**。核对`ChiZhang-805/fluffy-cat-journal`并输入`fluffy-cat-journal`确认。

更新脚本只允许已核验的基线，逐个核对SHA，保留原Pages配置、网址和无关文件；分支期间变动或文件冲突会停止，不force push、不新建仓库。`-CheckOnly`可只读检查。只有实际网页及CSS/JS都匹配才报告部署验证成功。

**不要运行历史上的`site/Publish-GitHub-Pages.cmd`。** 本次连接尝试创建功能分支返回403，未创建分支或提交；交付此包不代表线上已更新。

旧研究文档与v5–v15报告继续保留作历史资料，不代表当前启用的AI路线，也不能把历史测试数累计成本轮结果。图标许可见`licenses/Lucide-LICENSE.txt`；不附带字体文件。
