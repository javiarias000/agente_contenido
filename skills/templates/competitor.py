from skills.templates.base_template import BaseTemplate, TemplateContext


class CompetitorTemplate(BaseTemplate):
    angle_type = "competitor"

    @property
    def required_inputs(self) -> list[str]:
        return ["competitor_name"]

    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        return """
ANGLE: Competitor Comparison / Switch Story
- Start from the audience's frustration with the competitor
- Show the switching moment (without being aggressive or disparaging)
- Highlight 2-3 specific advantages
- Use "I switched from X to Y because..." structure
- Be fair and factual, focus on benefits not attacks
"""
