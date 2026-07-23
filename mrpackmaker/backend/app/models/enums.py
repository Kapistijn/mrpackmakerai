"""Domain enums and shared types."""

from enum import Enum


class LoaderType(str, Enum):
    FABRIC = "fabric"
    FORGE = "forge"
    NEOFORGE = "neoforge"


class ThemeType(str, Enum):
    TECHNOLOGY = "technology"
    ADVENTURE = "adventure"
    MAGIC = "magic"
    EXPLORATION = "exploration"
    SURVIVAL = "survival"
    CUSTOM = "custom"


class DifficultyType(str, Enum):
    CASUAL = "casual"
    NORMAL = "normal"
    HARD = "hard"
    EXPERT = "expert"


class PerformancePreference(str, Enum):
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    VISUALS = "visuals"


class ShaderSupport(str, Enum):
    """How the exported pack should treat shaders.

    OFF      - no shader loader, no shader configs.
    OPTIONAL - bundle an Iris/Oculus-compatible loader so shaders *can* be
               enabled by the player, but do not force a pack.
    ENABLED  - bundle the loader, recommend a shaderpack and write shader
               configs so shaders work out of the box.
    """

    OFF = "off"
    OPTIONAL = "optional"
    ENABLED = "enabled"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    REVIEW = "review"
    READY = "ready"
    EXPORTED = "exported"


class ModSource(str, Enum):
    MODRINTH = "modrinth"
    CURSEFORGE = "curseforge"
