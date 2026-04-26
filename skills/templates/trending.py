from skills.templates.base_template import BaseTemplate, TemplateContext


class TrendingTemplate(BaseTemplate):
    angle_type = "trending"

    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        return """
ANGLE: Trending Topic / News Reaction
- Reference the current trend or news item in the hook
- Connect the trend back to the brand's value proposition
- Use language that feels timely ("Everyone is talking about...", "Have you seen...")
- Keep it lightweight and shareable
"""
