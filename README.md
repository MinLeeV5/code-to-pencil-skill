# code-to-pencil

`code-to-pencil` 用于把现有页面实现转换成可校验、可追溯的 Pencil 基线稿。它通过扫描代码、构造结构化 `pencil --prompt` 输入，并校验生成后的 `.pen`，减少对运行态截图的依赖。

## 适用场景

当运行态界面不适合作为唯一事实来源时，可以使用这个 Skill，例如：

- 目标页面依赖登录态、缓存、本地状态或远程数据
- 运行态页面难以稳定停留在目标状态
- 第三方嵌入区域只应保留占位，不应固化真实内容
- 需要让生成的 `.pen` 能回溯到代码入口、资源和关键状态分支

## 仓库结构

```text
.
|-- SKILL.md
|-- README.md
|-- agents/openai.yaml
|-- references/
`-- scripts/
    |-- build_pencil_prompt.py
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
.agent/skills/code-to-pencil/scripts/validate_pen.py
```

## 基本流程

1. 用 `scripts/build_pencil_prompt.py` 扫描目标页面源码
2. 用 `pencil --workspace --out --prompt ...` 生成 `.pen`
3. 用 `scripts/validate_pen.py` 做结构校验
4. 用 Pencil 截图检查关键 frame 是否合理
5. 如果进入 interactive / headless 修补链路，显式执行 `save()`

## 使用要点

- 优先相信代码，而不是当前运行态截图
- 对不稳定的第三方嵌入内容使用中性占位
- 让生成结果保持可评审、可追溯、可继续迭代
- 不要假设 interactive 或 headless 修改会自动保存
