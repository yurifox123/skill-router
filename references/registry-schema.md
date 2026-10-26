# Registry schema

This reference is read only after Skill Router is active and a registry format needs to be created or repaired. It is linked from the skill description, but it is not part of inactive skill discovery.

The agent-facing registry is JSON Lines at `<library>/registry.jsonl`, with one object per skill. Router maintenance also generates `<library>/registry.md` as a readable table. The Markdown file is derived output; do not edit either generated catalog by hand.

```json
{
  "name": "playwright-skill",
  "purpose": "Browser automation and end-to-end testing",
  "tags": ["browser", "web", "e2e"],
  "requires": [],
  "source": "library",
  "path": "packages/playwright-skill",
  "size_bytes": 13930,
  "token_estimate": 3296,
  "sha256": "..."
}
```

`name`, `purpose`, `tags`, `requires`, `source`, `path`, `size_bytes`, `token_estimate`, and `sha256` are stable fields. `requires` is a list of skill names. `source` is normally `library` after migration and may retain the original root for inventory reports.

The router should refresh both generated files when inventory changes, read registry rows through the helper script, and inspect full skill instructions only after the user selects a skill.
