from skills.templates.base_template import BaseTemplate, TemplateContext


class CompetitorTemplate(BaseTemplate):
    angle_type = "competitor"

    @property
    def required_inputs(self) -> list[str]:
        return ["competitor_name"]

    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        brand_specific = ""
        if "mi idea" in ctx.brand_name.lower():
            brand_specific = """
CONTEXTO - MI IDEA (Corte Láser):
- Frustración del competidor: "Tardan semanas", "El diseño personalizado es caro", "Mala calidad"
- Ventajas de Mi Idea: Rápido (48-72 horas), precio accesible, precisión láser, diseño personalizado sin costo extra
- Ejemplo: "Cambié de [Competidor] a Mi Idea porque: precisión perfecta, entrega rápida, y el diseño personalizado se hace sin cargo extra"
- Diferenciales clave: Tecnología láser moderna, equipo creativo, respuesta rápida
"""

        return f"""
ANGLE: Competitor Comparison / Switch Story
{brand_specific}
- Comienza desde la frustración del cliente con el competidor
- Muestra el cambio sin ser agresivo o despectivo
- Destaca 2-3 ventajas específicas
- Estructura: "Cambié de [Competidor] a {ctx.brand_name} porque..."
- Sé justo y factual, enfócate en beneficios no en ataques
- Tone: {ctx.tone_of_voice}
"""
