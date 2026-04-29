from skills.templates.base_template import BaseTemplate, TemplateContext


class EducationalTemplate(BaseTemplate):
    angle_type = "educational"

    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        brand_specific = ""
        if "mi idea" in ctx.brand_name.lower():
            brand_specific = """
CONTEXTO - MI IDEA (Corte Láser & Diseño):
- Enseña sobre: "Cómo diseñar un empaque de regalo que venda", "Tips de diseño láser"
- Datos sorprendentes: "El 80% de regalos corporativos no tienen personalización"
- Tips prácticos: Materiales que mejor soportan grabado, diseño ergonómico, tiempos de producción
- Mención de Mi Idea: "Con la tecnología láser correcta, estos diseños tardan solo X horas"
- Establece autoridad en diseño y personalización
"""

        return f"""
ANGLE: Educational / Value-First
{brand_specific}
- Abre con un dato sorprendente, mito a desmentir, o "¿Sabías que..."
- Enseña 2-3 tips accionables relacionados al dominio de {ctx.brand_name}
- Mención suave de {ctx.brand_name} como la herramienta que lo hace posible
- Cierra con engagement: "¿Cuál tip te fue más útil? Comenta abajo"
- Establece autoridad sin ser predicador
- Tone: {ctx.tone_of_voice}
"""
