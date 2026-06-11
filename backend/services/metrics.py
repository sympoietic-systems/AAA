import json

from backend.api.schemas import MetricsInfo


class MetricsService:
    @staticmethod
    def store(metrics_repo, message_id: int, metrics: dict, recommendations: dict | None) -> None:
        s_t = metrics.get("pairwise_similarity")
        novelty = metrics.get("conceptual_novelty")
        if s_t is None:
            s_t = 0.0
        if novelty is None:
            novelty = 0.0

        temp_rec = None
        pres_rec = None
        freq_rec = None
        homeo_state = None
        if recommendations:
            t = recommendations.get("temperature")
            p = recommendations.get("presence_penalty")
            f = recommendations.get("frequency_penalty")
            if isinstance(t, dict):
                temp_rec = t.get("value")
            if isinstance(p, dict):
                pres_rec = p.get("value")
            if isinstance(f, dict):
                freq_rec = f.get("value")
            homeo_state = recommendations.get("state")

        phase_shifts = metrics.get("phase_shifts")
        phase_shifts_json = json.dumps(phase_shifts) if phase_shifts else None

        metrics_repo.insert(
            message_id=message_id,
            s_t=float(s_t),
            novelty=float(novelty),
            deficit=float(metrics["homeostatic_deficit"]) if metrics.get("homeostatic_deficit") is not None else 0.0,
            rolling_entropy=float(metrics["rolling_entropy"]) if metrics.get("rolling_entropy") is not None else None,
            coupling=float(metrics["coupling_coherence"]) if metrics.get("coupling_coherence") is not None else None,
            agent_divergence=float(metrics["agent_self_divergence"]) if metrics.get("agent_self_divergence") is not None else None,
            reverse_perturbation=float(metrics["reverse_perturbation"]) if metrics.get("reverse_perturbation") is not None else None,
            surprise_index=float(metrics["surprise_index"]) if metrics.get("surprise_index") is not None else None,
            mutual_perturbation=float(metrics["mutual_perturbation"]) if metrics.get("mutual_perturbation") is not None else None,
            vitality=float(metrics["conversation_vitality"]) if metrics.get("conversation_vitality") is not None else None,
            phase_shifts=phase_shifts_json,
            boringness=float(metrics["boringness"]) if metrics.get("boringness") is not None else None,
            conceptual_velocity=float(metrics["conceptual_velocity"]) if metrics.get("conceptual_velocity") is not None else None,
            divergence_resolution_ratio=float(metrics["divergence_resolution_ratio"]) if metrics.get("divergence_resolution_ratio") is not None else None,
            paskian_health=float(metrics["paskian_health"]) if metrics.get("paskian_health") is not None else None,
            temperature_rec=float(temp_rec) if temp_rec is not None else None,
            presence_penalty_rec=float(pres_rec) if pres_rec is not None else None,
            frequency_penalty_rec=float(freq_rec) if freq_rec is not None else None,
            homeostatic_state=homeo_state,
        )

    @staticmethod
    def build_info(metrics: dict | None) -> MetricsInfo | None:
        if not metrics:
            return None
        return MetricsInfo(
            pairwise_similarity=metrics.get("pairwise_similarity"),
            conceptual_novelty=metrics.get("conceptual_novelty"),
            rolling_entropy=metrics.get("rolling_entropy"),
            coupling_coherence=metrics.get("coupling_coherence"),
            agent_self_divergence=metrics.get("agent_self_divergence"),
            reverse_perturbation=metrics.get("reverse_perturbation"),
            surprise_index=metrics.get("surprise_index"),
            mutual_perturbation=metrics.get("mutual_perturbation"),
            homeostatic_deficit=metrics.get("homeostatic_deficit"),
            conversation_vitality=metrics.get("conversation_vitality"),
            boringness=metrics.get("boringness"),
            conceptual_velocity=metrics.get("conceptual_velocity"),
            divergence_resolution_ratio=metrics.get("divergence_resolution_ratio"),
            paskian_health=metrics.get("paskian_health"),
            phase_shifts=metrics.get("phase_shifts"),
        )

    @staticmethod
    def build_history(row: dict) -> MetricsInfo | None:
        if row.get("s_t") is None:
            return None
        return MetricsInfo(
            pairwise_similarity=row.get("s_t"),
            conceptual_novelty=row.get("novelty"),
            rolling_entropy=row.get("rolling_entropy"),
            coupling_coherence=row.get("coupling"),
            agent_self_divergence=row.get("agent_divergence"),
            reverse_perturbation=row.get("reverse_perturbation"),
            surprise_index=row.get("surprise_index"),
            mutual_perturbation=row.get("mutual_perturbation"),
            homeostatic_deficit=row.get("deficit"),
            conversation_vitality=row.get("vitality"),
            boringness=row.get("boringness"),
            conceptual_velocity=row.get("conceptual_velocity"),
            divergence_resolution_ratio=row.get("divergence_resolution_ratio"),
            paskian_health=row.get("paskian_health"),
            phase_shifts=None,
        )

    @staticmethod
    def build_recommendations(recs: dict | None):
        from backend.api.schemas import HomeostaticRecommendations
        if not recs:
            return None
        return HomeostaticRecommendations(
            temperature=recs.get("temperature"),
            presence_penalty=recs.get("presence_penalty"),
            frequency_penalty=recs.get("frequency_penalty"),
            state=recs.get("state", "healthy"),
            triggered_flags=recs.get("triggered_flags", []),
        )

    @staticmethod
    def parse_phase_shifts(raw: str | None) -> list[dict] | None:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None
