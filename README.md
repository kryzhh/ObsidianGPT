# ObsidianGPT

Local RAG chat over an Obsidian vault.

## Run

1. Ensure `.env.json` contains a valid `VAULT` path and `CHAT_MODEL`.
2. Start Ollama and pull required models (for example `nomic-embed-text`).
3. Run:

```bash
python main.py
```

## Indexing Behavior

- The app creates `chroma.db` on first run.
- On later runs, it compares the current markdown vault snapshot with the last indexed snapshot.
- If files were added/edited/removed, it automatically rebuilds the index.
- You can force rebuild at any time:

```bash
python main.py --reindex
```
