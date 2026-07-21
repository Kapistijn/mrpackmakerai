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


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    REVIEW = "review"
    READY = "ready"
    EXPORTED = "exported"


class ModSource(str, Enum):
    MODRINTH = "modrinth"
    CURSEFORGE = "curseforge"
