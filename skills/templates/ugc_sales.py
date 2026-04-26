from skills.templates.base_template import BaseTemplate, TemplateContext


class UGCSalesTemplate(BaseTemplate):
    angle_type = "sales"

    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        return f"""
ANGLE: UGC Sales / Direct Response
- Open with a relatable PROBLEM the target audience faces
- Position the brand as the SOLUTION
- Include social proof (e.g., "I've been using this for X weeks and...")
- End with a clear CTA (link in bio, swipe up, comment X)
- Tone: {ctx.tone_of_voice}
- Audience: {ctx.target_audience}
- Keep language conversational and authentic, avoid corporate speak
"""
