#!/usr/bin/env python3
"""Select the Pencil-facing CLI that matches the current invoking agent."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence


DEFAULT_EXECUTABLES = {
    'codex': 'codex',
    'claude-code': 'claude',
}

CODEX_SIGNAL_VARS = (
    'CODEX_THREAD_ID',
    'CODEX_SHELL',
    'CODEX_CI',
    'CODEX_INTERNAL_ORIGINATOR_OVERRIDE',
)

CLAUDE_CODE_SIGNAL_PREFIXES = (
    'CLAUDE_CODE_',
    'CLAUDECODE_',
)


class CliSelectionError(RuntimeError):
    """Raised when the launcher cannot resolve a matching CLI."""


def normalize_agent(agent: str | None) -> str | None:
    if agent is None:
        return None

    normalized = agent.strip().lower().replace('_', '-').replace(' ', '-')
    aliases = {
        'claude': 'claude-code',
        'claude-code': 'claude-code',
        'codex': 'codex',
    }
    if normalized in aliases:
        return aliases[normalized]

    raise CliSelectionError(
        f"Unsupported agent '{agent}'. Expected one of: {', '.join(sorted(aliases))}."
    )


def detect_agent(env: Mapping[str, str]) -> str:
    if any(env.get(name) for name in CODEX_SIGNAL_VARS):
        return 'codex'

    if any(key.startswith(CLAUDE_CODE_SIGNAL_PREFIXES) and env.get(key) for key in env):
        return 'claude-code'

    raise CliSelectionError(
        'Unable to determine the invoking agent. '
        'Pass --agent or set PENCIL_CLI_AGENT explicitly.'
    )


def resolve_agent(explicit_agent: str | None, env: Mapping[str, str]) -> str:
    if explicit_agent:
        return normalize_agent(explicit_agent)

    env_agent = env.get('PENCIL_CLI_AGENT')
    if env_agent:
        return normalize_agent(env_agent)

    return detect_agent(env)


def executable_env_var_name(agent: str) -> str:
    return f"PENCIL_CLI_COMMAND_{agent.upper().replace('-', '_')}"


def resolve_executable(
    agent: str,
    env: Mapping[str, str] | None = None,
    which=shutil.which,
) -> str:
    env = env or os.environ
    override_name = executable_env_var_name(agent)
    executable = env.get(override_name) or DEFAULT_EXECUTABLES.get(agent)

    if not executable:
        raise CliSelectionError(
            f"No CLI mapping is configured for agent '{agent}'. "
            f"Set {override_name} to the executable you want to use."
        )

    resolved = which(executable)
    if not resolved:
        raise CliSelectionError(
            f"Resolved agent '{agent}', but executable '{executable}' was not found in PATH. "
            f"Install it or override it via {override_name}."
        )

    return resolved


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Run the Pencil-facing CLI that matches the current invoking agent.'
    )
    parser.add_argument('--agent', help='Force the invoking agent, e.g. codex or claude-code')
    parser.add_argument(
        '--print-command',
        action='store_true',
        help='Print the resolved executable path and exit.',
    )
    parser.add_argument(
        'args',
        nargs=argparse.REMAINDER,
        help='Arguments to forward to the resolved executable. Prefix with -- to stop parsing.',
    )
    return parser.parse_args(list(argv))


def forwarded_args(raw_args: Sequence[str]) -> list[str]:
    if raw_args and raw_args[0] == '--':
        return list(raw_args[1:])
    return list(raw_args)


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    env = env or os.environ
    args = parse_args(argv)

    try:
        agent = resolve_agent(args.agent, env)
        executable = resolve_executable(agent, env=env)
    except CliSelectionError as exc:
        print(f'[FAIL] {exc}', file=sys.stderr)
        return 1

    if args.print_command:
        print(executable)
        return 0

    cmd_args = forwarded_args(args.args)
    if not cmd_args:
        print(
            '[FAIL] No arguments were provided for the resolved CLI. '
            'Pass the downstream command after --, or use --print-command.',
            file=sys.stderr,
        )
        return 1

    completed = subprocess.run([executable, *cmd_args], check=False)
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
