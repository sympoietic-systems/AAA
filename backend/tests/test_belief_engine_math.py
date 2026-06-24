import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.modules.belief_engine import (
    calculate_concept_density,
    parse_vector_16d,
)
from backend.modules.belief_math import (
    compute_delta_mass,
    compute_delta_confidence,
    clamp_mass,
    clamp_confidence,
    compute_lifecycle_stage,
)
from backend.utils.similarity import cosine_similarity


class TestConceptDensity:
    def test_empty_text_returns_zero(self):
        result = calculate_concept_density("")
        assert result == 0.0

    def test_text_with_no_lexicon_match_returns_zero(self):
        result = calculate_concept_density("xyzzy foo bar nothing matches here")
        assert result == 0.0

    def test_text_with_philosophical_terms_positive(self):
        text = "The rhizomatic ontology of posthuman thought deterritorializes structures"
        result = calculate_concept_density(text)
        assert result > 0.0
        assert result <= 1.0

    def test_density_scales_with_lambda(self):
        text = "The nomad traverses the rhizome through the plane of immanence"
        d1 = calculate_concept_density(text, lambda_param=10.0)
        d2 = calculate_concept_density(text, lambda_param=1.0)
        assert d1 < d2

    def test_density_bounded_by_one(self):
        from backend.modules.structural_engine import LEXICON_MAPPINGS
        stems = []
        for group in LEXICON_MAPPINGS:
            stems.append(group[0])
        dense_text = " ".join(stems)
        result = calculate_concept_density(dense_text, lambda_param=1.0)
        assert 0.0 <= result <= 1.0


class TestParseVector16d:
    def test_empty_json_returns_none(self):
        assert parse_vector_16d("") is None
        assert parse_vector_16d("[]") is None

    def test_16d_list_parses_correctly(self):
        vec = np.random.randn(16).astype(np.float32)
        json_str = json.dumps(vec.tolist())
        result = parse_vector_16d(json_str)
        assert result is not None
        assert len(result) == 16
        np.testing.assert_array_almost_equal(result, vec)

    def test_32d_list_returns_none(self):
        vec = np.zeros(32).tolist()
        result = parse_vector_16d(json.dumps(vec))
        assert result is None

    def test_dict_with_v16d_key_parses(self):
        vec = np.arange(16, dtype=np.float32)
        json_str = json.dumps({"v16d": vec.tolist()})
        result = parse_vector_16d(json_str)
        assert result is not None
        assert len(result) == 16

    def test_dict_with_v384d_key_returns_none_for_16d(self):
        vec = np.arange(384, dtype=np.float32)
        json_str = json.dumps({"v384d": vec.tolist()})
        result = parse_vector_16d(json_str)
        assert result is None

    def test_invalid_json_returns_none(self):
        assert parse_vector_16d("not json") is None
        assert parse_vector_16d("{broken") is None

    def test_none_value_returns_none(self):
        assert parse_vector_16d(None) is None


class TestCosineSimilarityWrapper:
    def test_identical_vectors_return_one(self):
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        result = cosine_similarity(a, a)
        assert abs(result - 1.0) < 0.001

    def test_orthogonal_vectors_return_zero(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        result = cosine_similarity(a, b)
        assert abs(result) < 0.001

    def test_dimension_mismatch_returns_zero(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        result = cosine_similarity(a, b)
        assert result == 0.0

    def test_opposite_vectors_return_negative_one(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        result = cosine_similarity(a, b)
        assert abs(result - (-1.0)) < 0.001


class TestDeltaMass:
    def test_positive_alignment_increases_mass(self):
        dm = compute_delta_mass(source_weight=0.4, alignment=0.8, current_mass=1.0)
        assert dm > 0

    def test_negative_alignment_decreases_mass(self):
        dm = compute_delta_mass(source_weight=0.4, alignment=-0.5, current_mass=1.0)
        assert dm < 0

    def test_high_mass_dampens_delta(self):
        dm_low = compute_delta_mass(source_weight=0.4, alignment=0.8, current_mass=0.5)
        dm_high = compute_delta_mass(source_weight=0.4, alignment=0.8, current_mass=2.5)
        assert abs(dm_high) < abs(dm_low)


class TestClampMass:
    def test_clamps_below_zero(self):
        assert clamp_mass(-0.5) == 0.0

    def test_clamps_above_three(self):
        assert clamp_mass(5.0) == 3.0

    def test_passes_through_normal_values(self):
        assert clamp_mass(1.5) == 1.5


class TestClampConfidence:
    def test_clamps_below_zero(self):
        assert clamp_confidence(-0.1) == 0.0

    def test_clamps_above_one(self):
        assert clamp_confidence(1.5) == 1.0


class TestLifecycleStage:
    def test_low_confidence_collapses(self):
        assert compute_lifecycle_stage("crystallized", 1.0, 0.10) == "collapsed"

    def test_low_mass_collapses(self):
        assert compute_lifecycle_stage("crystallized", 0.01, 0.5) == "collapsed"

    def test_very_low_mass_below_threshold_collapses(self):
        assert compute_lifecycle_stage("crystallized", 0.0005, 0.5) == "collapsed"

    def test_nucleation_crystallizes_on_high_mass(self):
        assert compute_lifecycle_stage("nucleation", 0.6, 0.5) == "crystallized"

    def test_crystallized_stays_crystallized(self):
        assert compute_lifecycle_stage("crystallized", 2.0, 0.8) == "crystallized"

    def test_senescence_recovers_on_high_mass(self):
        assert compute_lifecycle_stage("senescence", 0.6, 0.5) == "crystallized"

    def test_low_mass_returns_nucleation(self):
        assert compute_lifecycle_stage("nucleation", 0.05, 0.5) == "nucleation"

    def test_moderate_mass_returns_accretion(self):
        assert compute_lifecycle_stage("nucleation", 0.2, 0.5) == "accretion"
