from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TemplateContext:
    brand_name: str
    tone_of_voice: str
    target_audience: str
    brand_values: list[str]
    style_notes: str
    platform: str
    target_duration: int


class BaseTemplate(ABC):
    angle_type: str = "base"

    @abstractmethod
    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        ...

    @property
    def required_inputs(self) -> list[str]:
        return []

    def validate_inputs(self, inputs: dict) -> None:
        for key in self.required_inputs:
            if not inputs.get(key):
                raise ValueError(f"Template '{self.angle_type}' requires input: {key}")
