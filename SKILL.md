---
name: code-to-pencil
description: 当需要把现有页面实现转换成 Pencil 基线稿，并且运行态截图不稳定、页面状态容易被缓存、鉴权态或第三方内容污染时使用。
---

# Code To Pencil

## Overview

使用这个 skill 时，目标不是“让 Pencil 自由发挥生成 UI”，而是把现有代码实现收敛成一份**可追溯、可校验、可继续迭代**的 Pencil 基线稿。

默认采用 `code-first` 路线：先扫描代码，再构造结构化 `pencil --prompt`，最后对 `.pen` 做结构与可视校验。运行态截图只作为补充 sanity check，不作为单一事实来源。

当页面内存在大量稳定、重复出现的 UI primitive（如 input shell、主按钮、tabs、二维码容器、协议勾选行）时，可在 `code-first` 之上启用 `component-first` 模式：先抽组件 contract，再用组件实例拼页面 frame。目标是让 Pencil 基线稿更像“用代码里的组件搭页面”，而不是每次重画一遍。

能力归属：

- skill 源码放在独立 git 仓库中，便于后续单独发布到 GitHub
- 项目可通过 symlink 或其他本地映射方式，把它暴露为 `.agent/skills/code-to-pencil`
- 在项目内使用时，优先走 `.agent/skills/code-to-pencil/...` 路径，避免把仓库绝对路径写死

## Hard Rules

- 把页面代码、组件、hooks、资源 import 当作第一事实来源；运行态截图只做辅助。
- 如果目标状态依赖登录态、缓存、服务端返回或第三方 iframe，且无法在 1-2 步内稳定复现，不要先绕路清状态再截图，直接走 `code-first`。
- `pencil --prompt` 的输入必须显式列出 source files、目标 frame、忽略项、第三方区域处理方式和校验要求。
- 第三方 iframe、二维码授权、外部账号态等不稳定内容，只保留容器和中性占位，不固化真实用户数据。
- 生成后的 `.pen` 不能只看命令退出成功；至少要做 JSON 校验、顶层 frame 检查，以及一次 Pencil 截图复审。
- 顶层页面 frame 必须带 `context` 或等价注释，说明 source files、忽略项和特殊约束。
- 当同类控件在多个 frame 中重复出现时，优先抽成可复用组件 contract，再实例化到页面；不要在每个 frame 中重新发明输入框、按钮或 tab 的皮肤。
- 组件 contract 必须可追溯到具体 source files、基础视觉 token 和已知 states；如果只是“看起来差不多”，不要强行抽象成组件。
- Pencil 相关 CLI 默认应与当前触发 skill 的 Agent 保持一致；Codex 会话优先走 `codex`，Claude Code 会话优先走 `claude`，必要时通过 `.agent/skills/code-to-pencil/scripts/run_pencil_cli.py` 做显式选择与校验。

## Read First

- `references/pencil-cli-prompt-workflow.md`
- `references/prompt-contract.md`
- `references/validity-checklist.md`

## Workflow

### 0. Decide If Runtime Capture Is Optional

优先判断当前页面是否适合直接走代码复刻：

- 适合：登录页、表单页、列表页、分栏页、由明显状态机控制的页面
- 不适合依赖截图：需要先清登录态、切环境、重置缓存、等待第三方内容加载、依赖随机/实时数据的页面

如果运行态不能稳定进入目标页，直接跳过截图，进入下一步。

### 1. Collect Code Facts

先锁定页面入口和核心组件：

- 页面入口：app route / page component
- 关键 section / component
- 关键 hooks / store
- 资源文件：`png`、`svg`、`jpg`、`webp`

执行：

```bash
python .agent/skills/code-to-pencil/scripts/build_pencil_prompt.py \
  --page login \
  --pen uidesign/login.pen \
  --frame login-phone-default \
  --frame login-wechat-tab \
  --ignore "Legal copy is out of scope in this iteration" \
  --third-party "Treat embedded auth widgets as neutral placeholders" \
  --files \
    src/pages/Login/index.tsx \
    src/features/auth/LoginPage.tsx \
    src/features/auth/PhoneLogin.tsx \
    src/features/auth/EmbeddedAuthLogin.tsx \
    src/components/PhoneInput.tsx \
    src/components/CaptchaInput.tsx \
    src/components/QrCodeFrame.tsx \
  > /tmp/login-pencil-prompt.txt
```

如果只是想先看扫描结果，可加 `--dump-context-json`。

### 1.5. Decide If Component-First Is Worth It

遇到以下场景时，优先在 prompt 和评审中显式启用 `component-first`：

- 同类输入框、按钮、tab、容器在 2 个以上 frame 中重复出现
- 页面属于登录、表单、设置、列表筛选等“骨架稳定、控件重复”的类型
- 你预期后续会继续扩展同系列页面或补更多派生状态

此时先抽一层组件 contract：

- `component name`
- `source files`
- `base geometry / spacing / colors / radius`
- `states`
- `allowed overrides`
- `do not redesign`

如果页面只是一次性基线稿，或者每个 section 视觉差异很大，可以继续只用 `code-first`，不必为组件化而组件化。

### 2. Run Pencil In Prompt Mode

用上一步生成的 prompt 驱动 Pencil CLI：

```bash
python .agent/skills/code-to-pencil/scripts/run_pencil_cli.py --print-command

pencil \
  --workspace /absolute/path/to/repo \
  --out /absolute/path/to/repo/design/login.pen \
  --prompt "$(cat /tmp/login-pencil-prompt.txt)"
```

要求：

- 先确认当前会话会选中与 Agent 一致的 CLI；必要时用 `--agent` 或 `PENCIL_CLI_AGENT` 显式覆盖
- 如果你本地对 `codex` / `claude` 做了包装，再把 `--workspace`、`--out`、`--prompt` 等 Pencil 参数透传给该包装命令
- 总是让 prompt 包含明确的 source files 与 frame names
- prompt 中明确写“prefer code over current runtime screenshot”

### 3. Validate The Generated Pen

先做结构校验：

```bash
python .agent/skills/code-to-pencil/scripts/validate_pen.py \
  design/login.pen \
  --require-frame login-phone-default \
  --require-frame login-wechat-tab
```

再做 Pencil 复核：

- 用 `pencil interactive -i <pen> -o <tmp.pen>` 打开
- 调 `get_editor_state({ include_schema: false })`
- 至少对 1-2 个关键 frame 执行 `get_screenshot`
- 如果在 interactive / headless 模式里做了修改，显式执行 `save()`；不要假设会自动落盘

### 4. Review Against Code, Not Against Hunches

复审重点：

- 是否引用了真实资源路径
- 是否保留了代码中明确存在的状态 affordance
- 是否把第三方内容错误地“设计化”
- 是否因为省略某些区域而导致语义失真
- 如果启用了 `component-first`，同类控件是否真的来自同一组件 contract，而不是看起来相似但细节漂移

如果发现缺口，优先补 prompt contract，不要只修当前页面。

## Component-First Mode

`component-first` 不是要求 Pencil 先拥有“设计工具原生组件库”，而是要求 skill 先在 prompt / context / review 层建立一套组件 contract。

### What Counts As A Component Contract

只有满足以下条件时，才值得抽组件：

- 在代码里有明确来源，而不是来自运行态猜测
- 在页面中重复 2 次以上，或预期会被同系列页面复用
- 可以说清 base state 和 derived states
- 可以说清哪些属性允许 page-level override，哪些不允许

推荐优先抽这类组件：

- input shell
- helper / error text row
- primary button
- tabs
- agreement row
- qr container

### Assembly Rules

启用 `component-first` 时：

1. 先定义页面会用到哪些组件 contract
2. 再为每个 contract 标注 base state 与 derived states
3. 最后在页面 frame 中实例化这些 contract，并只做布局层 override

页面层应尽量只描述：

- 布局位置
- 当前 state
- 必要的文案差异
- 明确允许的 override

页面层不应重复定义：

- 同一输入框的圆角、底色、内边距
- 同一按钮的基础皮肤
- 同一第三方容器的占位策略

### Third-Party And Dynamic Regions

即使启用了 `component-first`，第三方与动态区仍然只能抽“容器 contract”，不能抽真实内容：

- 微信 / OAuth iframe
- 二维码内芯
- 第三方账号头像、昵称、实时内容

这些区域只能保留：

- 外层容器尺寸
- 内层占位尺寸
- loading / expired 等本地代码明确控制的 overlay
- 中性 placeholder 文案

## Prompt Requirements

构造给 Pencil 的 prompt 时，必须包含这些段落：

1. Goal：本次要复刻哪个页面
2. Source files：明确文件列表
3. Output：目标 `.pen` 路径和 frame names
4. Rules：优先代码、忽略项、第三方占位规则
5. Deliverables：需要创建哪些 frame、哪些 context/source 注释
6. Validation hints：生成后需要可读、可评审、可继续迭代

如果启用了 `component-first`，再额外包含：

7. Component contracts：列出页面复用的 primitives / sections、来源文件、基础状态与允许 override
8. Assembly rule：明确“prefer reusing the same component contract over redrawing similar controls”

详细模板见 `references/prompt-contract.md`。

## Route-Specific Notes

### Login / Auth Pages

- 默认优先 code-first，因为运行态很容易被登录缓存污染
- 协议、隐私、登录中、倒计时、二维码过期等派生状态，优先从 code branch / hook 中抽取
- 第三方登录内芯按容器处理，除非代码仓库自己持有完整 UI
- 当登录页同时存在 phone / wechat / bind / password 等近亲形态时，优先抽 auth-tabs、phone-input-shell、captcha-input-shell、primary-submit-button、agreement-row、qr-container 这类 contract，再分别实例化各状态

### Dashboard / Workspace Pages

- 如果页面骨架稳定，但内容数据动态，优先抽骨架、空态、错误态、关键分支态
- 只要截图需要大量前置数据清理，就回退到 code-first

## Deliverables

完成一次 code-to-pencil 任务时，至少交付：

- 目标 `.pen`
- 关键 frame 名称清单
- 资源来源说明
- 派生状态/忽略项说明
- 校验结果

如果启用了 `component-first`，再补充：

- 组件 contract 清单
- 每个 contract 对应的 source files
- 每个页面 frame 对 contract 的实例化关系

## What Not To Do

- 不要把当前浏览器/桌面端刚好看到的状态，当成唯一真相
- 不要为了截图去做长链路环境清理，最后偏离设计任务
- 不要把外部 iframe 的账号昵称、头像、二维码内容硬编码进 `.pen`
- 不要跳过 `.pen` 校验直接宣称“已完成”
- 不要把“长得像”当成“同一个组件”；只有当来源、token 和 state 都能说清楚时，才抽组件 contract
