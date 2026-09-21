# 2026-09-21 · 状态栏与记录书写精修

本次基于 `ChiZhang-805/fluffy-cat-journal` 已部署的源代码，保留原猫图层、极简入口、语音、DeepSeek 下拉菜单与原地趴睡；没有重新设计界面或加入跳跃。

## 实际改动

**状态栏。** 继续使用 393 × 852 的设计坐标，重绘蜂窝信号、Wi-Fi、电池的独立 SVG 轮廓并校准尺寸、位置及间距。时钟改为设备本地 H:mm，一秒检查一次；切换页面回来立即同步，不跟随动画暂停。

**正在书写的项目。** 原先顶部裁剪使活动 Notes 标题消失，只能看到它在底部的循环副本。现在标题、文字、书写线共享同一逻辑行原点。活动标题固定在 y=436；前爪可能轻微遮住边缘，但不会把标题滚到其他项目的位置。

**横线。** 根据每一个视觉行的实际墨迹下边缘 +3 px 放置书写线。文字折行时，各视觉行都有自己的横线，不再用下一项标题前的分隔线代替。

**中文手写。** 给“跑步”等常见运动汉字、数字与单位补充项目自绘的单线笔路。其他字符从本机可用楷体提取中心线，去阶梯并描成有轻重的墨迹。完成后不再盖回方正的印刷字形。笔尖和墨迹仍然使用同一条连续路径；字形种子固定，循环回来不会变化。没有分发任何字体文件，也不加载外部字体 CDN。

**动画。** 换项先抬笔、再送纸、最后落筆；小猫目光略滞后于笔尖，但不平滑或改变实际笔尖坐标。Great job! 的手写和撒花时间协同缩短 15%，仍等用户点击 Continue。睡觉、放笔、现有表单和语音流程保留。

**缓存。** HTML 中的 CSS/JS 地址加入 `v=20260921-detail-v3`，避免更新时混用旧代码。

## 测试

```sh
node --test tests/core.test.cjs
CHROMIUM_PATH=/usr/bin/chromium python tests/browser_test.py
CHROMIUM_PATH=/usr/bin/chromium python tests/refinement_test.py
```

实际通过：7 项单元测试、26 项原浏览器断言、32 项本版浏览器断言，共 65 项。
浏览器使用 Chromium 运行实际源码的内存文档；麦克风/API 使用明确测试替身，时钟测试使用可控的设备时间。

检查覆盖：Notes 顶部可见、标题/内容/横线同步、笔尖和墨迹一致、循环保留字形、换项抬笔、边界无位置跳变、长文本、跨分钟及后台恢复、6 种视口和原有语音授权/取消逻辑。

当前环境阻止浏览器打开本地或测试 URL，因此没有把内存源码检查说成线上 URL 或 iPhone 实机检查。截图来自实际运行的本版源码。

## 已知边界

- 时钟是真实设备本地时间；信号、Wi-Fi 和电池是状态栏外观，不读取真实设备信号或电量。
- SVG 是本项目重绘的外观，不是 iOS 原生状态栏控件；Windows 和 Apple 平台的系统字体、抗锯齿可能不同。尚未完成 iPhone/Safari 实机逐像素比对，不宣称“零偏差”。
- 罕见字符依赖本机字形中心线；不宣称回退路径遵守汉字标准笔顺。文本内容和可访问性文字保持用户确认值。
- 本轮没有真实 DeepSeek Key 或真实麦克风端到端测试，没有修改密钥存储策略。
- GitHub 连接读取正常，但写入返回 403 `Resource not accessible by integration`；这次没有远程成功提交。现有仓库的更新工具在源码包外层，由用户自己的 GitHub CLI 登录执行。
- Windows 更新工具已做静态和清单审查，当前环境没有 PowerShell，尚未在 Windows 真实登录环境运行。它会先核验远程文件，发现冲突就停止，只有网页及关键资源通过内容校验才宣告上线成功。

## 参考资料

- Apple 设计资源：https://developer.apple.com/design/resources/
- Apple 状态栏设计：https://developer.apple.com/design/human-interface-guidelines/status-bars
- JavaScript Date：https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date
- Git trees：https://docs.github.com/en/rest/git/trees
- Git references：https://docs.github.com/en/rest/git/refs
- Pages 发布源：https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
