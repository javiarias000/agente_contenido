from skills.templates.base_template import BaseTemplate, TemplateContext


class TrendingTemplate(BaseTemplate):
    angle_type = "trending"

    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        brand_specific = ""
        if "mi idea" in ctx.brand_name.lower():
            brand_specific = """
CONTEXTO - MI IDEA (Corte Láser):
- Tendencias relacionadas: DIY, regalos personalizados, emprendimiento creativo, diseño artesanal
- Oportunidades: "Todos están creando negocios de regalos personalizados"
- Conexión: Mi Idea como enabler de esas tendencias (tecnología láser, diseño rápido)
- Ejemplo: "Viral: cajas personalizadas para regalos corporativos - así las hago en 48 horas"
"""

        return f"""
ANGLE: Trending Topic / News Reaction
{brand_specific}
- Referencia la tendencia o noticia en el hook
- Conecta la tendencia a la propuesta de valor de {ctx.brand_name}
- Lenguaje actual ("Todos están hablando de...", "¿Ya viste...")
- Ligero y compartible, muestra cómo la marca se aprovecha del trend
- Tone: {ctx.tone_of_voice}
"""
