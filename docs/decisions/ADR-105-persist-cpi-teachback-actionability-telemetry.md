# ADR-105: Persistence & API Wiring of CPI, Teachback Ratio, and Actionability

**Date:** 2026-10-05  
**Status:** accepted  
**Deciders:** Antigravity, Vasily  

## Context

In ADR-098, conversational progress metrics were introduced to model grounded conversational dynamics:
- **`cpi` (Conversational Progress Index)**: \(\sqrt{\text{velocity} \times \text{teachback} \times \text{actionability}}\)
- **`teachback_ratio`**: Paskian uptake symmetry measuring the human's assimilation and re-use of concepts
- **`actionability`**: Density of concrete code, equations, tests, and operational directives
- **`collapse_pressure`**: Sycophancy-attractor drag metric
- **`phase_transition_magnitude`**: Disjoint centroid displacement magnitude

While these metrics were computed in `ConversationMetricsModule`, they were not persisted to the SQLite `conversation_metrics` table or mapped in `MetricsRepository`. As a consequence, historical queries via `GET /metrics` and conversation re-renders returned `null` for these fields (rendered as `"-"` in the UI).

## Decision

1. **Database Schema & Migration**:
   - Created migration `m053_add_cpi_teachback_actionability_collapse_pressure.py` to add `cpi`, `teachback_ratio`, `actionability`, `collapse_pressure`, and `phase_transition_magnitude` (`REAL`) columns to `conversation_metrics`.
   - Updated `m050_baseline_schema.py` so fresh databases initialize with these columns directly.
2. **Storage Entity & Row Mapping**:
   - Extended `MetricsRecord` dataclass in `backend/storage/models.py`.
   - Updated `_row_to_metrics` in `backend/storage/row_mappers.py` to read the columns safely.
3. **Repository & Service Layer**:
   - Updated `MetricsRepository.insert()` and `MetricsRepository.get_aggregates()` in `backend/storage/repositories/telemetry/metrics.py`.
   - Updated `MetricsService.store()` in `backend/services/metrics.py` to extract and persist the new metrics.
4. **API Endpoint**:
   - Updated `get_metrics()` in `backend/api/routes/metrics.py` to map `cpi`, `teachback_ratio`, `actionability`, `collapse_pressure`, and `phase_transition_magnitude` into `latest_info` and `history_items`.

## Consequences

- **Full Telemetry Persistence**: Live and historical metrics across conversation turns retain all grounded progress and allostatic indicators.
- **Frontend Alignment**: The side panel Vitality gauges (`cpi`, `tb`, `act`, `cp`) display stored and live telemetry values across historical turns without falling back to empty indicators (`"-"`).
