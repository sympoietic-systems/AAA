# EmbeddingGemma 2 vs MiniLM retrieval and storage

Fixture: `embedding-mrl-retrieval-v1` (`1414bf0bb9b127fe65e0a2b813ab1d3dd471cd82909873f6e240770f985f3c51`)
Labels: hand-authored synthetic query-to-document labels; diagnostic fixture, not a general retrieval benchmark

| Model | Dim | Recall@1 | Recall@3 | Recall@5 | MRR | Query ms | Document ms | Model RSS delta | Raw vector bytes | SQLite bytes after checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| minilm | 384 | 0.9 | 1.0 | 1.0 | 0.95 | 85.768 | 334.138 | 116514816 | 46080 | 73728 |
| embeddinggemma2 | 128 | 1.0 | 1.0 | 1.0 | 1.0 | 7125.023 | 39264.837 | 808886272 | 15360 | 32768 |
| embeddinggemma2 | 256 | 1.0 | 1.0 | 1.0 | 1.0 | 7306.133 | 38420.783 | 808886272 | 30720 | 53248 |
| embeddinggemma2 | 512 | 1.0 | 1.0 | 1.0 | 1.0 | 7138.503 | 38520.742 | 808886272 | 61440 | 135168 |
| embeddinggemma2 | 768 | 1.0 | 1.0 | 1.0 | 1.0 | 7059.462 | 39292.266 | 808886272 | 92160 | 135168 |

This synthetic corpus is a harness check, not a broad external retrieval benchmark. SQLite files contain only benchmark IDs and vectors in isolated model/dimension namespaces. No production vectors or database are read or migrated.
