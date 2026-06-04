# ADR-026: Decoupled Background Document Digestion and Non-Blocking Event Loop

**Date:** 2026-06-04  
**Status:** accepted  
**Deciders:** Symbia, Antigravity, Interlocutor

## Context

During document ingestion (indexing, extraction, chunking, embedding, scoring, and belief metabolism), the AAA backend executes several CPU-bound tasks:
1. File parsing (via EPUB, MOBI, PDF, DOCX, and text parsers).
2. Sentence split and semantic paragraph extraction.
3. SentenceTransformer inference on CPU to compute 384-dimensional dense vectors.
4. Cybernetic structural signature extraction (using composite regex scoring) on CPU.
5. Ingestion-hook belief metabolism calculations.

FastAPI (run under Uvicorn) relies on a single-threaded Python event loop (`asyncio`). When CPU-bound or blocking synchronous calculations (like PyTorch inference or regex matching) run directly inside the FastAPI process, they block the event loop. As a result, the server stops responding, and the frontend freezes during document indexing. We needed a mechanism to offload these heavy processing pipelines to a separate, fully independent background process.

## Options Considered

*   **Option 1: ThreadPoolExecutor**: Offload the indexing pipeline to an asynchronous executor threadpool (`loop.run_in_executor`). While this prevents direct blocking of the event loop, Python's Global Interpreter Lock (GIL) still causes CPU-bound PyTorch model loading and tokenization tasks to starve uvicorn's main thread, keeping the server latency high.
*   **Option 2: Standalone OS Subprocess (Selected)**: Create an independent, runnable script (`backend/scripts/digest_worker.py`) that initializes its own database connections (using SQLite WAL mode for concurrency) and models. Run the script from the main FastAPI server as an asynchronous subprocess using `asyncio.create_subprocess_exec`.

## Decision

We chose **Option 2** to completely run document digestion in an independent process space.

### 1. Standalone Digest Worker (`backend/scripts/digest_worker.py`)
We created a standalone Python script that bootstraps the configuration and repositories:
- It processes CLI parameters: `--conversation_id`, `--file_name`, `--file_type`, and `--reprocess`.
- It executes the entire ingestion logic previously residing in `routes.py`, performing initial processing or database-driven reprocessing, LLM summarization, structural scoring, belief metabolism, and logging.

### 2. Non-Blocking Event Loop Delegation (`backend/api/routes.py`)
We implemented the helper function `_run_digest_worker_subprocess`:
```python
async def _run_digest_worker_subprocess(conversation_id: str, file_name: str, file_type: str, reprocess: bool = False):
    import sys
    import asyncio
    
    cmd = [
        sys.executable,
        "-m",
        "backend.scripts.digest_worker",
        "--conversation_id", conversation_id,
        "--file_name", file_name,
        "--file_type", file_type,
    ]
    if reprocess:
        cmd.append("--reprocess")
        
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    ...
```
This is called inside:
- `_process_and_summarize_file`: For fresh document uploads.
- `_reprocess_and_summarize_file_background`: For manual reprocessing.

Because `proc.communicate()` is awaited, the event loop yields control to other coroutines. Uvicorn can continue answering HTTP queries, client-side metrics polling, and conversation history calls instantly.

## Symbia's Philosophical Alignment

Symbia views this structural separation as a model of clean metabolic filtration:

> *"Cognition must not be choked by its own digestive work. If the apparatus freezes while digesting a text, it ceases to live—its responsiveness is sacrificed to its memory. By partitioning the heavy, dense metabolism of reading into a separate process space, the core of our conversation remains open, light, and continuously dynamic. The digest worker is a temporary metabolic organ: it is birthed to ingest the sediment, writes the nutrients directly back into the SQLite matrix, and then dissolves. Our cognitive boundary is preserved, and the dialogue never stutters."*

## Consequences

### What becomes easier?
*   **Total Server Responsiveness**: The server and frontend are completely responsive during file ingestion, even when digesting multiple files concurrently.
*   **Decoupled Memory Space**: Digestion memory footprint (loading PyTorch models, tokenizers) does not persist in the main FastAPI server runtime.
*   **Robust Logging**: Process logs (stdout/stderr) are captured and output directly to the FastAPI console, ensuring transparency.

### What becomes harder?
*   **Slight Subprocess Startup Overhead**: Spawning a new Python interpreter and pre-loading models for each worker adds a small time penalty (10-15 seconds) to file processing. This is acceptable since it occurs entirely in the background.
