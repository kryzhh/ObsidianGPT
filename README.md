# ObsidianGPT

Local RAG chat over an Obsidian vault.

## Run

1. Ensure `.env.json` contains a valid `VAULT` path and `CHAT_MODEL`. (See `.env-example.json`)
2. Start Ollama and pull required models (for example `nomic-embed-text`(REQUIRED) and a chat model like `qwen2.5:3b`).
3. Run:

```bash
python main.py
```

## Indexing Behavior

- The app creates `chroma.db` on first run.
- On later runs, it hashes markdown file content and only re-embeds files whose content changed.
- Unreadable files and embedding failures are logged and skipped instead of crashing the whole run.
- Pass `--watch` to keep the index fresh in the background while you chat.
- You can force rebuild at any time:

```bash
python main.py --reindex
```
