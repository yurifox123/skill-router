# Registry schema

The machine registry is JSON Lines at `<library>/registry.jsonl`, with one object per skill. `inventory --write` also generates `<library>/registry.md` as a human-readable table. The Markdown file is derived output; do not edit it by hand.

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

The router should read registry rows through the helper script and only inspect full skill instructions after the user selects a skill.
