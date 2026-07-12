from backend.services.research.steps.base import BaseResearchStep, ResearchStepRegistry  # noqa: F401
from backend.services.research.steps.consolidate import ConsolidateStep  # noqa: F401
from backend.services.research.steps.digest import DigestStep  # noqa: F401
from backend.services.research.steps.document_digestion import DocumentDigestionStep  # noqa: F401
from backend.services.research.steps.evaluate import EvaluateStep  # noqa: F401
from backend.services.research.steps.parse import ParseStep  # noqa: F401
from backend.services.research.steps.plan import PlanStep  # noqa: F401
from backend.services.research.steps.reflect import ReflectionStep  # noqa: F401
from backend.services.research.steps.search import SearchStep  # noqa: F401
from backend.services.research.steps.synthesize import SynthesizeStep  # noqa: F401

# Register all 9 pipeline steps
ResearchStepRegistry.register("planning", PlanStep)
ResearchStepRegistry.register("document_digestion", DocumentDigestionStep)
ResearchStepRegistry.register("searching", SearchStep)
ResearchStepRegistry.register("parsing", ParseStep)
ResearchStepRegistry.register("digesting", DigestStep)
ResearchStepRegistry.register("consolidating", ConsolidateStep)
ResearchStepRegistry.register("reflection", ReflectionStep)
ResearchStepRegistry.register("evaluating", EvaluateStep)
ResearchStepRegistry.register("synthesizing", SynthesizeStep)
