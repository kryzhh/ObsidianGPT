# Mockingbird 

**What if you could talk to your second brain?**


Mockingbird is a local-first AI assistant that lets you have natural conversations with your personal knowledge base. Built on a RAG (Retrieval-Augmented Generation) pipeline using LangChain, ChromaDB, and Ollama, it runs entirely on your machine — no cloud, no API keys, no data leaving your device.
Currently supports Markdown files with intelligent chunking that preserves heading structure, metadata-aware retrieval that understands dates, filenames, and note types, and smart routing that distinguishes between personal and technical content. Planned support for PDFs, Word documents, and plain text files.

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

## WebUI
Currently in the [test](https://github.com/kryzhh/obsidiangpt/tree/test) branch. Work in progress.
