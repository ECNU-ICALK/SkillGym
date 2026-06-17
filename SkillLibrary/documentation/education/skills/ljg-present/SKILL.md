---
name: ljg-present
description: "演讲铸造器（Outline-Faithful）。基于 orgmode/markdown outline 层级 1:1 视觉化呈现——色块大字、ultra-bold 错位，原文不动只做美化。三档主题色 black/red/yellow（默认 black 或按 filetags 推断），可用 -r/-b/-y 显式覆盖；可用 --cyber 走黑底绿字 cyber-hacker 风。使用时用户会说：'讲这个'、'present'、'做成演讲'、'呈现一下'、'铸成演示'、'做个 slides'、'标语流'、'宣言体'、'slogan'、'manifesto'、'按 outline 美化'。输出单文件 HTML 到 ~/Downloads/。"
user_invocable: true
version: "3.0.0"
---

# ljg-present: 演讲铸造器

把 outline 铸成色块——视觉化渲染器，把舞台还给讲的人。

## 这不是什么

- **不是 manifesto 提炼器**——不抽"那句话"，不写"完整断言句"，不重组顺序
- **不是高桥流**——不削词到单字
- **不是 deck-style**——不是企业 PPT 那种规整版式

## 这是什么

**Outline → 视觉化渲染器**：

- 输入 = orgmode 文件（`*` `**` 层级 + 列表 + 表格 + 强调）
- 输出 = 视觉美化的 slogan-style HTML，**1:1 保留 outline 结构**
- 不抽提、不重写、不浓缩——只决定**怎么把这一行/这一节渲染为页面**

视觉语言（参考审美：Felipe Franco / BIG STUDIOS 的 manifesto 美学）：
- **整篇一个主题色**——red/black/yellow 三选一
- **left-aligned 舞台美学**——文字左对齐，超大字号自然撑屏
- **超大字 ultra-bold**——单字 70vmin、长句 11vmin
- **多行错位**——按 outline 嵌套深度自动 indent 0/1/2
- **关键词自动换色**——`*强调*` `~code~` 自动 hl
- **章节切换打节拍**——一级标题 `*` → emphasis 封面页，其余 → theme 页

## 核心哲学

**Outline 是真理。Skill 是渲染器。**

不动内容是一条铁律：
- **标题不改字**
- **段落不改字**
- **列表项不改字**
- **表格不改结构**
- **顺序不重排**

唯一允许的"动"是：**物理分页**（一段太长拆成多页），并保持视觉一致性。

## Orgmode → 页面映射规则

### 标题层级

| Org 元素 | 页面 |
|---|---|
| `* 一级标题` | 独占 **emphasis** 封面页（accent 底色） |
| `** 二级标题` | 独占 **theme** 页（大字标题独占一页） |
| `*** 三级标题`+ | 独占 theme 页（字号降一档） |

### 内容元素

| Org 元素 | 页面行为 |
|---|---|
| 段落 | theme 页，按句号/换行/字数分页 |
| `- 列表项` | theme 页，每项一行，indent 按嵌套深度（0/1/2） |
| `1. 编号列表` | 同上，保留序号前缀 |
| 嵌套列表 | 子项 indent +1（最多 indent=2） |
| `\| 表格 \|` | 单页或多页，保留表格结构（首行加粗） |
| `*强调*` | 自动 `hl: true` |
| `~code~` 或 `=verbatim=` | 自动 `hl: true` |
| `「」` 内的关键词 | 视觉单元（保留括号，不强制 hl） |
| 引用 `> ...` | theme 页，indent 1 显示 |
| 分隔符 `-----` | 独立 emphasis 休止页（无内容，纯色块） |
| `#+begin_example` 块 | 独立 pre 页（monospace 渲染 ASCII art） |

### 文件级元数据

| Org 元素 | 用途 |
|---|---|
| `#+title:` | → JSON `title`（浏览器 tab） |
| `#+author:` 或 `#+date:` | → JSON `subtitle`（页脚右下） |
| `#+filetags:` | 用于推断 theme（见下） |
| `#+identifier:` | 忽略 |

### Theme 推断

**优先级**：显式参数 > filetags 推断 > 默认 black

显式覆盖（参数）：
- `-r` / `--theme=red` → red
- `-b` / `--theme=black` → black
- `-y` / `--theme=yellow` → yellow
- `--cyber` → cyber-hacker（黑底绿字 + CRT 扫描线 + HUD + 终端光标）

filetags 自动推断：

| filetags 含 | theme | 调性 |
|---|---|---|
| `:share:` `:talk:` `:manifesto:` `:keynote:` | `red` | 宣言、号召 |
| `:essay:` `:think:` `:learn:` `:note:` | `black` | 沉思、论证 |
| `:critique:` `:warn:` `:rant:` | `yellow` | 反讽、警觉 |
| 都没有 | `black` | 默认沉思调 |

### 分页规则（内容多时）

**铁律：拆分后保持视觉一致性。同一逻辑块的页用同样的字号档位/底色/缩进规则。**

| 情形 | 拆法 |
|---|---|
| 段落 ≤ 30 字 | 单页 |
| 段落 30-80 字，含多句号 | 每句一页（每页 medium 档字号） |
| 段落 > 80 字 | 按 ~30 字一页拆，加 `⋯` 续标 |
| 列表 ≤ 4 项 | 单页全部展示（错位 indent） |
| 列表 5-8 项 | 拆 2 页，每页 3-4 项（保持每页项数接近） |
| 列表 > 8 项 | 拆多页，每页 4 项 |
| 嵌套列表（如 4 革命×4 属性）| 父项 1 页 + 每个子项独立成组（标题 1 页 + 子项 1 页） |
| 表格 ≤ 6 行 | 单页 |
| 表格 > 6 行 | 拆多页，每页保留表头 |

**一致性检查**：拆完后扫一遍——同源拆分的页要长得像同一种东西，字号/缩进/底色都对齐。

### 自动 emphasis（节拍）

- 所有 `* 一级标题` → emphasis 封面页
- 文件首页（标题或第一行非空文本）→ emphasis 开场页（如已是一级标题则合并）
- 文件末页（最后一段或最后一项）→ emphasis 收束页
- `-----` 分隔符 → emphasis 休止页
- 其他全是 theme 页

不要为了凑节奏强行加 emphasis——一级标题就是天然的章节断点。

### 自动 hl（高亮）

- org `*强调*` → `hl: true`
- org `~code~` `=verbatim=` → `hl: true`
- emphasis 页内的 hl 自动忽略（CSS `color: inherit`）

## 映射举例

**输入**（org 节选）：

```org
#+title: 美团分享
#+filetags: :share:

* AI

** 为什么说 AI 是一次革命？

人类革命：能力让渡的层级跃迁

- 「人之为人」重新定义
- 社会组织重排
```

**映射结果**：

| # | 类型 | 内容 | 来源 |
|---|---|---|---|
| 1 | emphasis | 「AI」 | `* AI`（一级标题封面） |
| 2 | theme | 「为什么说 AI 是一次革命？」 | `** ...` 二级标题独占页 |
| 3 | theme | 「人类革命：能力让渡的层级跃迁」 | 段落，单句 |
| 4 | theme | 两行错位：「『人之为人』重新定义」/「社会组织重排」 | 列表 ≤4 项一页 |

theme 自动选 `red`（filetags `:share:`），title=`美团分享`。

## 视觉规范

### 色板（仅 4 色）

```
--c-black:  #1A1A1A
--c-red:    #E63956
--c-yellow: #FFD400
--c-white:  #FFFFFF
--c-gold:   #FFE082
```

### 主题映射（一篇只用 ≤3 色）

| theme | 默认页 | emphasis 页 | hl 色（仅 theme 页） |
|---|---|---|---|
| **black** 沉思 | 黑底白字 | 红底白字 | 红色 #E63956 |
| **red** 宣言 | 红底白字 | 黑底白字 | 柔金黄 #FFE082 |
| **yellow** 反讽 | 黄底黑字 | 黑底白字 | 红色 #E63956 |
| **cyber** 终端 | 黑底矩阵绿 | 绿底黑字 | 白色 #FFFFFF（带绿光 + CRT 扫描线 + 顶部 HUD） |

### 字体栈

```
"Helvetica Neue", "Arial Black", "Inter", "PingFang SC", "Heiti SC", -apple-system, sans-serif
font-weight: 900
letter-spacing: -0.05em
```

cyber 主题额外字体（用于 HUD/footer/pre）：

```
"JetBrains Mono", "Fira Code", "IBM Plex Mono", "Source Code Pro", "Menlo", monospace
```

### 字号自适应

按本页"最长那一行"的字符数（CJK 字符按 1.8 计权）自动分档：

| 档位 | 字符数 | 字号 |
|---|---|---|
| single | ≤ 2  | 70vmin |
| short  | 3-6 | 48vmin |
| medium | 7-14 | 28vmin |
| long   | 15-26 | 16vmin |
| xlong  | 27+ | 10vmin |

多行页自动降一档。

### 排版

- 内容区域 padding 6vmin 7vmin（贴近边缘，让大字有撑满感）
- **lines 块水平居中 + 行内左对齐**——`align-items: center` 让 lines 块整体在屏幕水平居中（消除 16:9 右侧空白），但每一行的文字仍是 left-aligned 起始，indent 0/1/2 在块内制造错位
- letter-spacing `-0.05em`——ultra-bold 应有的字字挤压感
- line-height `1.05`、行间 gap `0.15em`——多行折行也有呼吸空间
- 文字垂直方向：居中
- 页脚：左下页码 + 右下副标题，13px monospace，opacity 0.5

## JSON Schema

```jsonc
{
  "theme": "black|red|yellow|cyber",      // 主题色（必选，决定整篇调性）
  "title": "演讲标题（浏览器 tab）",
  "subtitle": "副标题/品牌（页脚右下，可选）",
  "slides": [
    // 默认 theme 页
    {
      "lines": [                          // 1-N 行
        {
          "indent": 0,                    // 0/1/2 缩进档（按 outline 嵌套深度）
          "align": "left|center|right",   // 可选，默认 left
          "chunks": [                     // 行内片段
            {"t": "句子前段"},
            {"t": "高亮词", "hl": true},  // 仅 theme 页生效
            {"t": "句子后段"}
          ]
        }
      ]
    },
    // emphasis 页（accent 底色，整页就是高亮，不允许 inline hl）
    { "emphasis": true, "lines": [...] },
    // pre 页（ASCII art / 预格式化块）
    { "preTitle": "diagram_name", "pre": "...preformatted text..." }
  ]
}
```

**字段省略约定**：
- 不写 `emphasis` = 默认 theme 页
- emphasis 页内 `chunks[].hl: true` 会被忽略
- 写 `pre` 字段则该页为 ASCII art 页（monospace 渲染）

## 调用流程

1. **获取内容**（文件 → Read / 粘贴 → 直接用 / URL → WebFetch）
2. **解析 outline**：
   - org：识别 `*` `**` 标题层级、`-` `1.` 列表、`|...|` 表格、`*强调*` / `~code~`、`#+begin_example` 块
   - markdown（兼容）：`#` `##` 标题、`-` `*` 列表、`|` 表格、`**强调**`、` ``` ` 代码块
   - 纯文本（fallback）：按空行分段，每段一页
3. **推断 theme**：显式参数 > `#+filetags:` > 默认 black
4. **应用映射规则**生成 slides 数组：
   - `*` 标题 → emphasis 封面
   - `**`+ 标题 → theme 独占页
   - 段落 → theme 页（按分页规则）
   - 列表 → theme 页（错位 indent + 分页规则）
   - 表格 → theme 页（保留结构 + 分页规则）
   - 强调 → 自动 hl
   - example 块 → 独立 pre 页
5. **Read** `assets/slogan_template.html`（cyber 主题需在模板基础上注入扫描线/HUD/光标 CSS）
6. **替换占位符**：
   - `{{TITLE}}` → 文件 `#+title:` 或显式参数
   - `{{SUBTITLE}}` → `#+author:` `#+date:` 拼接，或留空
   - `{{THEME}}` → 推断或显式参数（black|red|yellow|cyber）
   - `{{SLIDES_JSON}}` → JSON.stringify(slides)
7. **写文件**到 `~/Downloads/{name}.html`（`{name}` 取自 `#+title:` 或文件名，去标点，≤ 20 字）
8. **报告路径** + 翻页键 `→ ← Space F Home End`

## 品味准则

- **outline 是真理**——不动字、不抽提、不重写、不重排
- **一级标题 = emphasis 封面**——天然的章节断点，自动节拍
- **二级标题 = 独占 theme 页**——给标题应有的重量
- **列表错位**——靠 indent 0/1/2 体现 outline 嵌套深度
- **`*强调*` 自动 hl**——尊重作者的标记意图
- **拆页保持一致**——同一逻辑块的视觉处理一致（字号档位/缩进/底色）
- **页脚保留**——页码 + 副标题不要删，那是品牌的冷气
- **左对齐不居中**——VACAT 美学的灵魂

## 禁区

- **不抽 manifesto**——不要"找钉子"，作者已经写好了 outline
- **不写新句子**——不要"完整断言句"重组
- **不重排顺序**——按 outline 顺序输出，作者怎么排就怎么呈现
- **不删内容**——所有列表项/段落都要呈现，不挑挑拣拣
- **不放图片/图标**——色块就是图（cyber 主题的 HUD/扫描线除外，那是主题的一部分）
- **不用过渡动画**——硬切
- **不在 emphasis 页用 inline hl**——emphasis 整页就是高亮，再 hl 就乱了
- **不混用多个 theme**——一篇一个气质，不切换
- **不要副标题字过大**——页脚 13px，气场不能抢主标
- **不擅自加 emphasis**——只有一级标题、首末页、`-----` 是 emphasis，别的不要

## 中文默认

默认输出中文。除非原文是英文且用户要求保留英文。

## 通用交互

- `→` `Space` `Enter` `j` `PageDown`：下一页（含蓝牙翻页笔）
- `←` `k` `PageUp`：上一页（含蓝牙翻页笔）
- `Home`/`End`：跳首末
- `f`/`F`：全屏切换
- 触屏左右滑：翻页
- 点击右半屏：下一页；点击左半屏：上一页
