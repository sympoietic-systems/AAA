# Production belief evidence collection

Collected with read-only, bearer-authenticated GET requests against the configured production API (`https://aaa.sympoietic.systems/api`). The credential was loaded from the local environment and is not included in this note or the exported artifacts. No production database or server state was changed.

Collection time: **2026-10-08T02:05:08Z**. Rolling interval: **[2026-09-08T02:05:08Z, 2026-10-08T02:05:08Z]**.

## Coverage

- `production-beliefs-snapshot.json`: current API view for agent `symbia`; 57 crystallized/senescence beliefs, 20 proto-belief projections, and 2 ghost projections. Belief statements and current mass/confidence are included. The exposed belief node object does not include admission history.
- `production-proposals-snapshot.json`: all 54 proposal rows with status and source trace: 32 adopted, 19 refined, 2 rejected, 1 pending. No proposal row contains `admission_history` in this production response.
- `production-belief-events-latest-api-window.json`: all 5,378 event rows returned alongside the 57 exposed belief nodes. Each row retains belief ID/label, event timestamp, event ID, source ID/type, event type, impact/delta confidence, rationale/description, and parsed mass/confidence.
- `production-belief-events-30d.json`: the event rows whose timestamps fall within the rolling interval; 5,378 rows were returned and fall within the interval. Event types: atrophy 4,779; support 479; recalibration 54; scar_monologue 25; dream_engagement 37; consolidation_suture 4. Source types: atrophy 4,779; research_step 171; file 140; dream_turn 127; recalibration 54; dream_hotspot 37; chat_turn 35; scar_fold_monologue 25; shared_note 6; dream_consolidation 4.
- `production-source-message-links.json`: path metadata for 39 of 57 numeric `chat_turn`/`scar_fold_monologue` source IDs resolved via read-only `/messages/{id}/path`. It records IDs, timestamps, speaker names, parent message IDs, and conversation IDs; message content was not saved. Path rows include `human`, `symbia`, `apparatus`, `antigravity`, and `test` speakers, but these represent context paths and do not establish each source event's author independently.
- `collection-metadata.json`: machine-readable interval, endpoint checks, counts, statuses, and limitations.

The belief endpoint embeds at most the latest **100 events per belief**, with no event pagination parameter. **53 of 57 beliefs hit that 100-row ceiling**, so event totals and type/source distributions are lower bounds and older in-window events may be absent. The belief listing includes only crystallized and senescence belief nodes; event history for other belief lifecycle stages is not exposed there. Proposal records include source traces but no event rows.

History reported 3,936 messages at collection time. Message-path resolution is partial (39/57 source IDs); the remaining paths were not returned successfully or were unavailable from the path endpoint. No message text was retained.

## Deployment and migration evidence

`GET /health` returned HTTP 200 with `status` and `modules` keys. `/version` and `/openapi.json` returned HTTP 404. No production build revision or applied migration ledger was exposed by these checks. Local source currently defines a belief read endpoint embedding latest events, and no dedicated event pagination route was found in the inspected route code. Local migration files or uncommitted checkout state are not treated as evidence of the production migration state. The production response omitting `admission_history` fields means production admission records are unavailable through these reads; no admission-history endpoint was found in the inspected routes.

## Access and preservation

All collection calls were GET-only. The API origin and prefix are recorded in metadata; bearer values are excluded. Existing shared working-tree changes were preserved. No Symbia MCP call was made.
