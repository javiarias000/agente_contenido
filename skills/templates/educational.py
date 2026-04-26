from skills.templates.base_template import BaseTemplate, TemplateContext


class EducationalTemplate(BaseTemplate):
    angle_type = "educational"

    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        return """
ANGLE: Educational / Value-First
- Lead with a surprising fact, myth-bust, or "did you know"
- Teach 2-3 actionable tips related to the brand's domain
- Soft mention of the brand as the tool that enables this
- End with an engagement hook: "Which tip was most helpful? Comment below"
- Establish authority without being preachy
"""
