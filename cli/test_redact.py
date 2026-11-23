"""Risk 1: what the backstop's redaction replaces, and what it must leave alone."""
import json
import unittest

from redact import MARK, redact, redact_text


class RedactTest(unittest.TestCase):
    def test_key_shapes_and_assignments_go(self):
        for text in ("key sk-ant-api03-" + "a1" * 12, "ghp_" + "A1b2" * 9,
                     "AKIA" + "ABCDEFGH12345678", "xoxb-1234567890-abcdef",
                     "Authorization: Bearer abc123def456ghi789",
                     "export OPENAI_API_KEY=sk9live0000000000abc", "--token=tok_1234567890abcd",
                     "https://user:hunter2pass@example.com/x",
                     "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIx\n-----END RSA PRIVATE KEY-----"):
            out = redact_text(text)
            self.assertIn(MARK, out, text)
            self.assertEqual(redact_text(out), out, "not idempotent")

    def test_lookalikes_stay(self):
        # every one of these fired on the first draft of the rules, over real config
        for text in ("usage = {'input_tokens': usage.input_tokens}", "token_budget = budget.max",
                     "tokens = n.tokens", "TOKEN=$(gh auth token)", "## Basic usage",
                     "token: 'some-name'", "max_tokens: 4096"):
            self.assertEqual(redact_text(text), text)

    def test_json_by_key_header_and_flag(self):
        cfg = {"mcpServers": {"t": {"env": {"TELEGRAM_BOT_TOKEN": "123:abc", "LOG_LEVEL": "info"},
                                    "headers": {"X-Custom": "anything"},
                                    "args": ["--api-key", "plainvalue", "--verbose", "x"]}},
               "techniques": {"Secret Wish Confession": "a prompt technique, not a secret"},
               "permissions": {"allow": ["Bash(git:*)"]}}
        out = json.loads(redact(json.dumps(cfg)))
        srv = out["mcpServers"]["t"]
        self.assertEqual(srv["env"], {"TELEGRAM_BOT_TOKEN": MARK, "LOG_LEVEL": "info"})
        self.assertEqual(srv["headers"], {"X-Custom": MARK})
        self.assertEqual(srv["args"], ["--api-key", MARK, "--verbose", "x"])
        self.assertEqual(out["techniques"], cfg["techniques"])
        self.assertEqual(out["permissions"], cfg["permissions"])

    def test_clean_json_keeps_its_exact_text(self):
        text = '{"a":1,  "model": "opus"}'   # odd spacing survives: the hash stays put
        self.assertEqual(redact(text), text)

    def test_redacted_json_is_idempotent(self):
        once = redact(json.dumps({"env": {"GITHUB_TOKEN": "ghp_" + "x1" * 18}}))
        self.assertEqual(redact(once), once)


if __name__ == "__main__":
    unittest.main()
