"""Pipeline subpackage for Adaptive Cover.

Provides a typed snapshot dataclass and a priority-ordered handler
chain that post-processes the coordinator's raw calculated position
before it is applied to physical covers.

Handler priority convention (higher number = runs first):
  100 — reserved for future "emergency" overrides
   95 — SecurityHandler  (human presence / away-mode)
   80 — WeatherHandler   (future)
   50 — default adaptive positioning (implicit — no handler needed)
"""

from .registry import PipelineRegistry
from .types import PipelineSnapshot

__all__ = ["PipelineRegistry", "PipelineSnapshot"]
