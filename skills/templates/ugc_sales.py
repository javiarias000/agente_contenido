from skills.templates.base_template import BaseTemplate, TemplateContext


class UGCSalesTemplate(BaseTemplate):
    angle_type = "sales"

    def system_prompt_additions(self, ctx: TemplateContext) -> str:
        brand_specific = ""
        if "mi idea" in ctx.brand_name.lower():
            brand_specific = """
CONTEXTO ESPECÍFICO - MI IDEA (Corte Láser & Diseño de Estructuras):
- El problema: Diseñadores y emprendedores necesitan productos personalizados de alta calidad
- La solución: Mi Idea ofrece corte láser profesional en MDF, acrílico, cartón con diseños únicos
- Casos de uso: Cajas personalizadas, letreros decorativos, estructuras de regalo, empaques profesionales
- Diferenciales: Personalización rápida, diseño personalizado, materiales de calidad, precisión láser
- Ejemplos concretos: "Esta caja de vino personalizada tardó solo 2 días en diseño y corte"
"""

        return f"""
ANGLE: UGC Sales / Direct Response
{brand_specific}
- Abre con un PROBLEMA relatable que enfrenta el público objetivo
- Posiciona {ctx.brand_name} como la SOLUCIÓN
- Incluye prueba social ("Hice esto en 3 días", "Los clientes amaron", "Perfecto para regalos")
- Termina con CTA claro (enlace en bio, sígueme, comenta X)
- Tono: {ctx.tone_of_voice}
- Audiencia: {ctx.target_audience}
- Lenguaje conversacional, auténtico, evita jerga corporativa
- Muestra el proceso creativo o el resultado final con entusiasmo
"""
