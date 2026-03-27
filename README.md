# code-to-pencil

`code-to-pencil` 用于把现有页面实现转换成可校验、可追溯的 Pencil 基线稿。它通过扫描代码、构造结构化 `pencil --prompt` 输入，并校验生成后的 `.pen`，减少对运行态截图的依赖。

当页面由稳定的重复控件组成时，它也支持在 `code-first` 之上启用 `component-first`：先抽组件 contract，再用组件实例组装页面 frame，让基线稿更接近“从代码组件库取控件搭页面”。

## 适用场景

当运行态界面不适合作为唯一事实来源时，可以使用这个 Skill，例如：

- 目标页面依赖登录态、缓存、本地状态或远程数据
- 运行态页面难以稳定停留在目标状态
- 第三方嵌入区域只应保留占位，不应固化真实内容
- 需要让生成的 `.pen` 能回溯到代码入口、资源和关键状态分支
- 页面内存在大量重复 UI primitive，希望统一输入框、按钮、tabs、容器的设计表达

## 仓库结构

```text
.
|-- SKILL.md
|-- README.md
|-- agents/openai.yaml
|-- references/
`-- scripts/
    |-- build_pencil_prompt.py
    |-- run_pencil_cli.py
    `-- validate_pen.py
```

## 在项目中接入

推荐通过 symlink 暴露到项目的 `.agent/skills`：

```bash
ln -s /absolute/path/to/code-to-pencil /path/to/project/.agent/skills/code-to-pencil
```

接入后，项目内可以直接使用这些路径：

```bash
.agent/skills/code-to-pencil/scripts/build_pencil_prompt.py
.agent/skills/code-to-pencil/scripts/run_pencil_cli.py
.agent/skills/code-to-pencil/scripts/validate_pen.py
```

## Agent 对齐的 CLI 选择

建议让 Pencil 相关 CLI 与当前触发 Skill 的 Agent 保持一致：

- Codex 触发时，优先走 `codex`
- Claude Code 触发时，优先走 `claude`

可通过统一入口脚本自动选择：

```bash
python .agent/skills/code-to-pencil/scripts/run_pencil_cli.py --print-command
```

选择优先级如下：

1. `--agent codex|claude-code`
2. `PENCIL_CLI_AGENT`
3. 当前会话环境自动探测

如果默认命令名不对，可分别覆盖：

```bash
PENCIL_CLI_COMMAND_CODEX=/custom/bin/codex
PENCIL_CLI_COMMAND_CLAUDE_CODE=/custom/bin/claude
```

如果检测到对应 Agent，但本机没有对应 CLI，脚本会直接报错，不会静默降级到别的 CLI。

## 基本流程

1. 用 `scripts/build_pencil_prompt.py` 扫描目标页面源码
2. 用 `pencil --workspace --out --prompt ...` 生成 `.pen`
3. 用 `scripts/validate_pen.py` 做结构校验
4. 用 Pencil 截图检查关键 frame 是否合理
5. 如果进入 interactive / headless 修补链路，显式执行 `save()`

如果页面结构稳定且控件复用度高，可在第 1 步和第 2 步之间插入一层组件抽取：

1.5. 定义 component contracts（来源文件、基础 token、states、allowed overrides）
1.6. 在 prompt 中要求优先复用这些 contracts，而不是重画相似控件

## 使用要点

- 优先相信代码，而不是当前运行态截图
- 对不稳定的第三方嵌入内容使用中性占位
- 重复控件优先抽成组件 contract，再实例化到页面
- 让生成结果保持可评审、可追溯、可继续迭代
- 不要假设 interactive 或 headless 修改会自动保存
