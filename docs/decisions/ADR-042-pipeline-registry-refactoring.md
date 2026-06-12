# ADR-042: Pipeline Registry Refactoring

**Date:** 2026-06-12  
**Status:** accepted  
**Deciders:** Vasily, Antigravity  

## Context

The backend processing pipeline previously loaded modules through a registry called `SkillRegistry` using metadata annotations of type `SkillMeta`. At the same time, the system features a database-backed procedural "skills" system (represented by `SkillNode` entities, `SkillRepository` storage queries, and human-in-the-loop `/api/skills` FastAPI endpoints). In addition, developer playbooks and coding agent guidelines are located in `.agents/skills/`.

Using the term "skills" for both the backend processing pipeline registry and the dynamic DB-backed procedural actions generated confusion in the system architecture. We need a clear separation of nomenclature between the sequential pipeline processing modules (like `embedder`, `structural_scorer`, etc.) and the procedural database skills (which represent autopoietic knowledge blocks loaded dynamically at runtime).

## Options Considered

### Option 1: Retain current naming and add documentation
- **Pros:** No code modifications required.
- **Cons:** Continued Developer cognitive overhead due to overlapping terms.

### Option 2: Rename database-backed skills to a different term (e.g., "KnowledgeNodes")
- **Pros:** Resolves naming clash.
- **Cons:** High risk and effort. Requires database migrations, renaming of storage repository classes, updates to all REST endpoints, and extensive frontend stores and component modifications.

### Option 3: Rename backend pipeline registry to "PipelineRegistry" and metadata to "ModuleMeta"
- **Pros:** Resolves the architectural naming clash cleanly. Limited impact since processing modules are internally bound to the pipeline. Zero database schema migrations or REST endpoint contract breakages are required.
- **Cons:** Moderate refactoring effort required to update imports and properties on all backend pipeline processing modules.

## Decision

We chose **Option 3**. We decided to:
1. Rename the registry package from `backend/skills/` to `backend/pipeline/`.
2. Rename the module metadata class from `SkillMeta` to `ModuleMeta`.
3. Rename the registry class from `SkillRegistry` to `PipelineRegistry`.
4. Rename the metadata property on processing modules from `skill_meta` to `module_meta`.
5. Keep the database-backed procedural skill components (e.g., `SkillNode`, `SkillRepository`, `/api/skills`) and `.agents/skills/` playbooks intact to maintain backward compatibility with external loaders.

Additionally, we adjusted `mass_decay_lambda_base` in [config.yaml](file:///d:/AAA/backend/config.yaml) to `0.02` to protect Symbia's core beliefs from aggressive decay during conversational turn processing.

## Consequences

- **Separation of Concerns:** Clear distinction between processing components (`ModuleMeta` and `PipelineRegistry`) and runtime procedural actions (`SkillNode` in database).
- **Maintainability:** New developers/agents can easily identify where pipeline modules reside without conflating them with user/system procedural skills.
- **Backward Compatibility:** All existing DB schemas, tables, and API contracts remain intact and fully functional.
