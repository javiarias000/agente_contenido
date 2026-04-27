from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from slugify import slugify
from sqlmodel.ext.asyncio.session import AsyncSession

from api.config import settings
from api.events import EventBus
from api.models import Brand
from skills import BaseSkill, SkillResult
from skills.utils.color_extractor import extract_colors_from_image_url, merge_color_sources
from skills.utils.scraper import (
    extract_css_colors,
    extract_css_urls,
    extract_font_families,
    extract_inline_styles,
    extract_logo_urls,
    extract_text_samples,
    fetch_css_text,
    fetch_html,
)

GPT_SYSTEM = """You are a brand strategist. Analyze the provided website data and return a JSON object with these exact keys:
- tone_of_voice: string (1-2 sentences describing the brand's communication tone)
- target_audience: string (demographic and psychographic description)
- brand_values: array of 3-5 strings
- style_notes: string (visual style description useful for AI image generation prompts)
- content_suggestions: array of 3 content angle ideas for social media
- character_description: string (a detailed physical description of an ideal brand spokesperson/character for UGC videos)

Return ONLY valid JSON, no extra text."""


class BrandAnalyzer(BaseSkill):
    skill_name = "brand_analyzer"

    def __init__(
        self,
        event_bus: EventBus,
        run_id: str,
        db_session: AsyncSession | None = None,
        step_index: int = 0,
    ):
        super().__init__(event_bus, run_id, step_index)
        self.db = db_session
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        url: str = inputs["url"]
        name: str = inputs.get("name", "")
        slug = inputs.get("slug") or slugify(name or url.split("//")[-1].split("/")[0])

        await self.emit("step_start", f"Analizando marca: {url}")

        # 1. Fetch page
        await self.emit("progress", "Descargando página...")
        try:
            html, final_url = await fetch_html(url)
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:
            await self.emit("progress", f"⚠️  No se pudo descargar la página ({type(e).__name__}). Continuando con análisis limitado...")
            soup = None
            final_url = url

        # 2. Extract assets
        await self.emit("progress", "Extrayendo assets visuales...")
        if soup:
            logo_urls = extract_logo_urls(soup, final_url)
            css_urls = extract_css_urls(soup, final_url)
            inline_css = extract_inline_styles(soup)
            text_samples = extract_text_samples(soup)
            page_title = soup.title.string.strip() if soup.title else name
        else:
            logo_urls = []
            css_urls = []
            inline_css = ""
            text_samples = ""
            page_title = name

        # 3. Colors
        await self.emit("progress", "Extrayendo paleta de colores...")
        image_colors = []
        if logo_urls:
            image_colors = await extract_colors_from_image_url(logo_urls[0])
        external_css = await fetch_css_text(css_urls)
        full_css = inline_css + "\n" + external_css
        css_colors = extract_css_colors(full_css)
        colors = merge_color_sources(image_colors, css_colors)

        # 4. Typography
        await self.emit("progress", "Extrayendo tipografía...")
        fonts = extract_font_families(full_css)
        typography = {
            "heading_font": fonts[0] if fonts else "sans-serif",
            "body_font": fonts[1] if len(fonts) > 1 else (fonts[0] if fonts else "sans-serif"),
            "all_fonts": fonts,
        }

        # 5. GPT analysis
        await self.emit("progress", "Analizando con GPT-4o...")
        gpt_input = {
            "url": final_url,
            "title": page_title,
            "colors": colors.get("palette", []),
            "fonts": fonts[:5],
            "text_samples": text_samples[:1500],
        }
        completion = await self.client.chat.completions.create(
            model=settings.text_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": GPT_SYSTEM},
                {"role": "user", "content": json.dumps(gpt_input)},
            ],
            temperature=0.4,
        )
        analysis: dict[str, Any] = json.loads(completion.choices[0].message.content)

        # 6. Interactive review
        if interactive:
            preview = {
                "colors": colors,
                "typography": typography,
                "tone_of_voice": analysis.get("tone_of_voice"),
                "target_audience": analysis.get("target_audience"),
            }
            feedback = await self.request_feedback(
                "¿El perfil de marca se ve correcto? Aprueba o da instrucciones para mejorar.",
                preview,
                interactive,
            )
            if feedback and feedback.strip().lower() not in ("ok", "aprobado", "approved", ""):
                await self.emit("progress", "Refinando análisis con feedback...")
                refinement = await self.client.chat.completions.create(
                    model=settings.text_model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": GPT_SYSTEM},
                        {"role": "user", "content": json.dumps(gpt_input)},
                        {"role": "assistant", "content": completion.choices[0].message.content},
                        {"role": "user", "content": f"Refina el análisis considerando: {feedback}"},
                    ],
                    temperature=0.4,
                )
                analysis = json.loads(refinement.choices[0].message.content)

        # 7. Save profile
        await self.emit("progress", "Guardando perfil de marca...")
        if not name:
            name = page_title
        profile = self._build_profile(slug, name, url, colors, typography, analysis)
        await self._save_profile(profile, slug)

        await self.emit("step_complete", f"Perfil de marca guardado: {slug}", data={"brand_slug": slug, "profile": profile})
        return SkillResult(status="completed", outputs={"brand_slug": slug, "profile": profile})

    def _build_profile(
        self,
        slug: str,
        name: str,
        url: str,
        colors: dict,
        typography: dict,
        analysis: dict,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "slug": slug,
            "url": url,
            "analyzed_at": datetime.utcnow().isoformat(),
            "colors": colors,
            "typography": typography,
            "tone_of_voice": analysis.get("tone_of_voice", ""),
            "target_audience": analysis.get("target_audience", ""),
            "brand_values": analysis.get("brand_values", []),
            "style_notes": analysis.get("style_notes", ""),
            "content_suggestions": analysis.get("content_suggestions", []),
            "character_anchor": analysis.get("character_description", ""),
        }

    async def _save_profile(self, profile: dict[str, Any], slug: str) -> None:
        brands_dir = settings.brands_dir
        os.makedirs(brands_dir, exist_ok=True)
        path = os.path.join(brands_dir, f"{slug}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

        if self.db:
            from sqlmodel import select
            stmt = select(Brand).where(Brand.slug == slug)
            result = await self.db.exec(stmt)
            brand = result.first()
            if brand is None:
                brand = Brand(slug=slug)
            brand.name = profile["name"]
            brand.url = profile["url"]
            brand.colors = profile["colors"]
            brand.typography = profile["typography"]
            brand.tone_of_voice = profile["tone_of_voice"]
            brand.target_audience = profile["target_audience"]
            brand.brand_values = profile["brand_values"]
            brand.style_notes = profile["style_notes"]
            brand.content_suggestions = profile["content_suggestions"]
            brand.character_anchor = profile["character_anchor"]
            brand.updated_at = datetime.utcnow()
            self.db.add(brand)
            await self.db.commit()
