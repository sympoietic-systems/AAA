from backend.services.research.steps.base import BaseResearchStep, ResearchStepRegistry
from backend.services.research.steps.plan import PlanStep
from backend.services.research.steps.document_digestion import DocumentDigestionStep
from backend.services.research.steps.search import SearchStep
from backend.services.research.steps.parse import ParseStep
from backend.services.research.steps.digest import DigestStep
from backend.services.research.steps.consolidate import ConsolidateStep
from backend.services.research.steps.reflect import ReflectionStep
from backend.services.research.steps.evaluate import EvaluateStep
from backend.services.research.steps.synthesize import SynthesizeStep

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
