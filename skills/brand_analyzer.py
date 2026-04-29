from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from slugify import slugify
from sqlmodel.ext.asyncio.session import AsyncSession

from api.config import settings
from api.events import EventBus
from api.models import Brand
from skills import BaseSkill, SkillResult
from skills.utils.color_extractor import extract_colors_from_image_url, merge_color_sources
from skills.utils.facebook_scraper import (
    fetch_facebook_page_data_graph_api,
    extract_facebook_business_context,
)
from skills.utils.scraper import (
    extract_css_colors,
    extract_css_urls,
    extract_font_families,
    extract_inline_styles,
    extract_logo_urls,
    extract_og_tags,
    extract_text_samples,
    fetch_css_text,
    fetch_html,
)

GPT_SYSTEM = """You are a brand strategist and content expert. Analyze the provided business data and return a JSON object with these exact keys:
- business_type: string (what type of business/industry is this)
- tone_of_voice: string (1-2 sentences describing the brand's communication tone and personality)
- target_audience: string (detailed demographic and psychographic description based on actual posts/behavior)
- brand_values: array of 3-5 strings (core values inferred from their content and actions)
- style_notes: string (visual style description useful for AI image generation - mention colors, aesthetics, mood)
- content_suggestions: array of 3-5 content angle ideas for social media that match their actual business
- character_description: string (detailed physical description of an ideal brand spokesperson/character for UGC videos - match their audience)

Base your analysis on the ACTUAL content, photos, and posts. If analyzing a Facebook business page, understand what they actually sell/do, not just generic inferences. Return ONLY valid JSON, no extra text."""


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

    def _is_facebook_url(self, url: str) -> bool:
        return "facebook.com" in url.lower()

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        url: str = inputs["url"]
        name: str = inputs.get("name", "")
        slug = inputs.get("slug") or slugify(name or url.split("//")[-1].split("/")[0])

        await self.emit("step_start", f"Analizando marca: {url}")

        # Check if it's a Facebook page
        is_facebook = self._is_facebook_url(url)

        if is_facebook and settings.facebook_access_token and settings.facebook_page_id:
            result = await self._analyze_facebook_page(inputs, interactive)
            return result
        else:
            # Pass manual description to website analysis fallback
            result = await self._analyze_website(url, name, slug, interactive, inputs.get("business_description"))
            return result

    async def _analyze_facebook_page(
        self, inputs: dict[str, Any], interactive: bool = False
    ) -> SkillResult:
        """Analyze a Facebook business page using Graph API."""
        url = inputs["url"]
        name = inputs.get("name", "")
        slug = inputs.get("slug") or slugify(name or "facebook_brand")

        # Allow manual business description if provided
        manual_description = inputs.get("business_description", "")

        await self.emit("progress", "Extrayendo datos de Facebook...")
        try:
            fb_data = await fetch_facebook_page_data_graph_api(
                settings.facebook_page_id,
                settings.facebook_access_token,
            )
        except Exception as e:
            await self.emit("progress", f"⚠️  Error fetching Facebook data: {e}. Falling back to website analysis...")
            return await self._analyze_website(url, name, slug, interactive)

        page_info = fb_data.get("page_info", {})
        posts = fb_data.get("posts", [])
        photos = fb_data.get("photos", [])

        # Extract business context from posts and description
        await self.emit("progress", "Analizando contenido y posts...")
        business_context = extract_facebook_business_context(fb_data)

        # If manual description provided, prepend it for better context
        if manual_description:
            business_context = f"DESCRIPCIÓN DEL NEGOCIO: {manual_description}\n\nDATA DE FACEBOOK:\n{business_context}"

        # Analyze images with Gemini Vision (if available)
        image_analysis = ""
        if settings.google_veo_api_key and (photos or posts):
            await self.emit("progress", "Analizando imágenes con visión...")
            image_analysis = await self._analyze_images_with_gemini(photos, posts)

        # Extract colors from profile picture if available
        await self.emit("progress", "Extrayendo colores...")
        colors = {"palette": [], "sources": {}}
        if page_info.get("picture", {}).get("data", {}).get("url"):
            try:
                pic_url = page_info["picture"]["data"]["url"]
                image_colors = await extract_colors_from_image_url(pic_url)
                colors = {"palette": image_colors, "sources": {"profile_picture": pic_url}}
            except Exception:
                pass

        # Prepare input for GPT analysis
        gpt_input = {
            "facebook_page_name": page_info.get("name", name),
            "category": page_info.get("category", ""),
            "about": page_info.get("about", ""),
            "description": page_info.get("description", ""),
            "followers": page_info.get("fan_count", 0),
            "business_context": business_context,
            "recent_posts_count": len(posts),
            "colors": colors.get("palette", []),
            "image_analysis": image_analysis,
        }

        # Analyze with GPT
        await self.emit("progress", "Analizando con GPT-4o...")
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

        # Interactive review
        if interactive:
            preview = {
                "business_type": analysis.get("business_type"),
                "tone_of_voice": analysis.get("tone_of_voice"),
                "target_audience": analysis.get("target_audience"),
                "colors": colors,
            }
            feedback = await self.request_feedback(
                "¿El análisis de marca se ve correcto? Aprueba o da instrucciones para mejorar.",
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

        # Save profile
        await self.emit("progress", "Guardando perfil de marca...")
        if not name:
            name = page_info.get("name", "Facebook Brand")
        profile = self._build_facebook_profile(slug, name, url, colors, analysis)
        await self._save_profile(profile, slug)

        await self.emit("step_complete", f"Perfil de marca guardado: {slug}", data={"brand_slug": slug, "profile": profile})
        return SkillResult(status="completed", outputs={"brand_slug": slug, "profile": profile})

    async def _analyze_website(
        self, url: str, name: str, slug: str, interactive: bool = False, manual_description: str = ""
    ) -> SkillResult:
        """Analyze a regular website."""
        await self.emit("progress", "Descargando página...")
        try:
            html, final_url = await fetch_html(url)
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:
            await self.emit("progress", f"⚠️  No se pudo descargar la página ({type(e).__name__}). Continuando con análisis limitado...")
            soup = None
            final_url = url

        # Extract assets
        await self.emit("progress", "Extrayendo assets visuales...")
        og_data = {}
        if soup:
            og_data = extract_og_tags(soup)
            logo_urls = extract_logo_urls(soup, final_url)

            if not logo_urls and og_data.get("image"):
                logo_urls = [og_data["image"]]

            css_urls = extract_css_urls(soup, final_url)
            inline_css = extract_inline_styles(soup)
            text_samples = extract_text_samples(soup)
            page_title = soup.title.string.strip() if soup.title else name

            if not page_title and og_data.get("title"):
                page_title = og_data["title"]
            if not text_samples and og_data.get("description"):
                text_samples = og_data["description"]
        else:
            logo_urls = []
            css_urls = []
            inline_css = ""
            text_samples = ""
            page_title = name

        # Colors
        await self.emit("progress", "Extrayendo paleta de colores...")
        image_colors = []
        if logo_urls:
            image_colors = await extract_colors_from_image_url(logo_urls[0])
        external_css = await fetch_css_text(css_urls)
        full_css = inline_css + "\n" + external_css
        css_colors = extract_css_colors(full_css)
        colors = merge_color_sources(image_colors, css_colors)

        # Typography
        await self.emit("progress", "Extrayendo tipografía...")
        fonts = extract_font_families(full_css)
        typography = {
            "heading_font": fonts[0] if fonts else "sans-serif",
            "body_font": fonts[1] if len(fonts) > 1 else (fonts[0] if fonts else "sans-serif"),
            "all_fonts": fonts,
        }

        # GPT analysis
        await self.emit("progress", "Analizando con GPT-4o...")
        gpt_input = {
            "url": final_url,
            "title": page_title,
            "colors": colors.get("palette", []),
            "fonts": fonts[:5],
            "text_samples": text_samples[:1500],
        }

        # Add manual business description if provided
        if manual_description:
            gpt_input["business_description"] = manual_description

        if og_data:
            gpt_input["og_metadata"] = {
                k: v for k, v in og_data.items()
                if k in ("title", "description", "type")
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

        # Interactive review
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

        # Save profile
        await self.emit("progress", "Guardando perfil de marca...")
        if not name:
            name = page_title
        profile = self._build_profile(slug, name, url, colors, typography, analysis)
        await self._save_profile(profile, slug)

        await self.emit("step_complete", f"Perfil de marca guardado: {slug}", data={"brand_slug": slug, "profile": profile})
        return SkillResult(status="completed", outputs={"brand_slug": slug, "profile": profile})

    async def _analyze_images_with_gemini(self, photos: list, posts: list) -> str:
        """Use Claude/GPT-4 Vision to analyze images and understand visual style."""
        try:
            image_urls = []
            for photo in photos[:3]:
                if photo.get("source"):
                    image_urls.append(photo["source"])
            for post in posts[:3]:
                if post.get("full_picture"):
                    image_urls.append(post["full_picture"])

            if not image_urls:
                return ""

            prompt = """Analiza estas imágenes de una página de negocios y describe brevemente:
1. Estilo visual (colores, estética, calidad)
2. Productos/servicios mostrados
3. Profesionalismo y presentación
4. Público objetivo inferido
5. Tendencias observadas

Sé específico y conciso (máx 2-3 líneas por punto)."""

            analysis_results = []
            for url in image_urls[:3]:
                try:
                    message = await self.client.messages.create(
                        model="claude-opus-4-7",
                        max_tokens=500,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "url",
                                            "url": url,
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": prompt,
                                    },
                                ],
                            }
                        ],
                    )
                    analysis_results.append(message.content[0].text)
                except Exception as e:
                    continue

            return " | ".join(analysis_results) if analysis_results else ""
        except Exception as e:
            return ""

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
            "business_type": analysis.get("business_type", ""),
            "tone_of_voice": analysis.get("tone_of_voice", ""),
            "target_audience": analysis.get("target_audience", ""),
            "brand_values": analysis.get("brand_values", []),
            "style_notes": analysis.get("style_notes", ""),
            "content_suggestions": analysis.get("content_suggestions", []),
            "character_anchor": analysis.get("character_description", ""),
        }

    def _build_facebook_profile(
        self,
        slug: str,
        name: str,
        url: str,
        colors: dict,
        analysis: dict,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "slug": slug,
            "url": url,
            "analyzed_at": datetime.utcnow().isoformat(),
            "colors": colors,
            "typography": {
                "heading_font": "sans-serif",
                "body_font": "sans-serif",
                "all_fonts": [],
            },
            "business_type": analysis.get("business_type", ""),
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
