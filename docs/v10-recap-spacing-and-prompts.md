# v10 · 回顾页留白与分类长按提示

## 修改范围

本版基于 `bb284721c5526effacbe5ceee92c9ddfc35cb1b9`（v9）整理。
保留全部六类记录、补记日期、双语菜单、原图角色、循环书写、庆祝、原地趴睡、回顾对话及计时。
没有改动评分算法、模型调用、已保存记录的字段或资产文件。

## 回顾页空间

画布继续为 393 × 852。顶部导航、系统时间、底部语音按钮的位置不动。
小猫实际 Canvas 渲染位置、点击区域、气泡、当天卡片一起上移44设计像素。

| 对象 | v9 | v10 |
|---|---:|---:|
| 小猫的 Canvas translateY | 45 | 1 |
| 气泡 top | 181 | 137 |
| 当天卡片 top | 308 | 264 |
| 当天卡片 height | 166 | 166 |
| 近7天卡片 top | 488 | 444 |
| 近7天卡片 height | 222 | 266 |
| 近7天卡片 bottom | 710 | 710 |
| 100分柱子绘制高度 | 79 | 135 |
| 语音按钮 top | 744 | 744 |

`js/review-layout.js` 集中给出共享几何数据。`animation.js` 只在 review 场景读取新坐标；
`review.js` 将相同参数应用到容器的局部CSS变量，并按真实的135像素绘图区换算柱高。
刻度、日期、数值顶部空间独立计算，100分不会越过标题。零分有基线标记，缺失数据仍然不绘制柱子。
情绪继续使用文字足迹，不为了填满空间而添加情绪高低评分。
柱子保留原来的依次升起动画；选择“减少动态效果”时直接呈现最终值。

## 记录页提示

| 板块 | 中文 | English |
|---|---|---|
| 运动 | 长按和小猫聊运动 | Hold to log your workout |
| 饮食 | 长按告诉小猫吃了啥 | Hold to share your meal |
| 情绪 | 长按和小猫说心情 | Hold to share how you feel |
| 睡眠 | 长按和小猫聊睡眠 | Hold to talk about sleep |
| 面部 | 长按说说今天的状态 | Hold to share your skin notes |
| 专注 | 长按告诉小猫你的计划 | Hold to tell me your plan |

提示只在原来的未填写完整状态显示，由 `entry-action.js` 的受控文案表选择。
填写完整、语音回填、清空、切换语言时按原规则刷新；进入授权、倾听和整理时仍使用忙碌状态。
普通记录的确认态为“完成并继续”，专注仍为“开始专注”或编辑/补记对应动作。
照片不算填空，可选营养的提交规则不变，不要求编造未知信息。
记录页语音仍显示在上方模块；回顾页语音仍在底部绿色按钮内。

## 实际验证

- 242 项 Node 单元测试通过，涵盖原业务规则以及新增文案/几何测试。
- 130 项本轮浏览器检查通过：六类、双语、六种尺寸、柱子比例/边界、空白日、动画/减少动态效果。
- 75 项记录按钮/文字聊聊回归检查通过。
- 63 项回顾页回归检查通过。
- 15 项对话、阅读暂停、取消和分享异步回归检查通过。
- 23 项交付单文件检查通过，其中包含实际手动记录、补记、书写、庆祝、回顾的路径。
- 65 处本轮涉及模块的命名函数/方法具备“输入、输出、功能”函数头注释；行内事件回调不纳入计数。

证据在外层 `verification/`，截图来自真实程序。预览对比使用相同的人工示例睡眠记录，
不代表用户真实记录。相应测试源在 `tests/`。

## 验证边界

本环境浏览器直接导航到 localhost 被管理员策略阻止；没有绕过策略。
测试以内存文档装载同一交付源码，注入隔离存储。语音/API回归使用明确的测试替身；
录音权限、真实麦克风、摄像头、个人API Key、iPhone/Safari没有在本轮实机验证。
这不影响对本轮实际DOM尺寸、文字、Canvas位置与CSS动画的检查，但不是线上部署验证。

GitHub连接尝试创建功能分支返回403，没有创建分支或提交。
外层更新器沿用已存在的仓库与Pages配置，在用户电脑上校验文件SHA并原子提交。
Windows/PowerShell端到端发布在本轮未运行，只有完成更新器的在线校验后才算网站已更新。

## 重现

```sh
npm test
python tests/refinement_v10_browser_test.py
python tests/interaction_v9_browser_test.py
python tests/review_browser_test.py
python tests/review_extra_test.py
python tools/build-standalone.py ../Fluffy-Cat-v10.html
python tests/standalone_v9_smoke.py ../Fluffy-Cat-v10.html
python tools/audit-comments.py ../verification/comments.json
```

浏览器脚本通过 `CHROMIUM_BIN` 指定浏览器路径，`FLUFFY_RESULTS` 指定证据位置。
`standalone_v9_smoke.py` 保留文件名以便回归追溯，已更新为本版的分类提示和回顾尺寸断言。
