# code-to-pencil

Turn an existing page implementation into a validated Pencil baseline by scanning code, building a structured `pencil --prompt` request, and verifying the generated `.pen`.

## What It Solves

`code-to-pencil` is for design extraction workflows where runtime screenshots are not a reliable source of truth.

Typical triggers:

- the target page depends on login state, cache, or remote data
- the runtime UI is hard to stabilize before capture
- embedded third-party widgets should be represented as placeholders
- the generated `.pen` needs to remain traceable back to source code

## Repository Layout

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

## Install In A Project

Expose the skill inside a project by linking it into `.agent/skills`:

```bash
ln -s /absolute/path/to/code-to-pencil /path/to/project/.agent/skills/code-to-pencil
```

After that, project-local calls can use:

```bash
.agent/skills/code-to-pencil/scripts/build_pencil_prompt.py
.agent/skills/code-to-pencil/scripts/validate_pen.py
```

## Basic Workflow

1. Scan page source files with `scripts/build_pencil_prompt.py`
2. Run `pencil --workspace --out --prompt ...`
3. Validate the generated `.pen` with `scripts/validate_pen.py`
4. Review key frames with Pencil screenshots
5. If interactive edits are made, explicitly call `save()`

## Notes

- Prefer code over the current runtime screenshot
- Treat unstable third-party embeds as neutral placeholders
- Keep generated frames reviewable and traceable to source files
- Do not assume interactive or headless edits auto-save
