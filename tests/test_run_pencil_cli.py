import importlib.util
import pathlib
import unittest

SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'run_pencil_cli.py'


def load_module():
    spec = importlib.util.spec_from_file_location('run_pencil_cli', SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f'Unable to load module from {SCRIPT_PATH}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunPencilCliTests(unittest.TestCase):
    def test_script_exists(self):
        self.assertTrue(SCRIPT_PATH.exists(), f'missing script: {SCRIPT_PATH}')

    def test_explicit_agent_wins_over_env_and_detection(self):
        module = load_module()
        resolved = module.resolve_agent('codex', {'PENCIL_CLI_AGENT': 'claude-code'})
        self.assertEqual(resolved, 'codex')

    def test_env_agent_wins_over_detection(self):
        module = load_module()
        resolved = module.resolve_agent(None, {'PENCIL_CLI_AGENT': 'claude-code'})
        self.assertEqual(resolved, 'claude-code')

    def test_detects_codex_from_environment(self):
        module = load_module()
        resolved = module.resolve_agent(None, {'CODEX_THREAD_ID': 'thread-123'})
        self.assertEqual(resolved, 'codex')

    def test_prefers_codex_when_both_agent_signals_exist(self):
        module = load_module()
        resolved = module.resolve_agent(
            None,
            {
                'CODEX_THREAD_ID': 'thread-123',
                'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
            },
        )
        self.assertEqual(resolved, 'codex')

    def test_missing_agent_signal_raises_clear_error(self):
        module = load_module()
        with self.assertRaises(module.CliSelectionError) as cm:
            module.resolve_agent(None, {})
        self.assertIn('Unable to determine', str(cm.exception))

    def test_missing_cli_raises_clear_error(self):
        module = load_module()
        with self.assertRaises(module.CliSelectionError) as cm:
            module.resolve_executable('codex', which=lambda _: None)
        self.assertIn('codex', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
