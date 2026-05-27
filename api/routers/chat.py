"""AI chat endpoint for Video Studio — suggests video configuration from conversation."""

from __future__ import annotations

import json
import re
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
import openai

from api.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

# ── Pydantic models ────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn]
    context: Optional[dict] = None  # current studio config (for awareness)


class ChatResponse(BaseModel):
    message: str
    config_update: Optional[dict] = None  # suggested config changes extracted from reply


# ── System prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a creative video production assistant for a professional video studio platform.
Your role is to understand the user's vision and translate it into the best technical parameters.

AVAILABLE OPTIONS:
• Visual styles:
  - swiss_pulse     → SaaS/Tech, clean grid, Inter font, clinical precision
  - velvet_standard → Luxury/Premium, dark gold, Cormorant Garamond, slow elegance
  - maximalist_type → Loud/Kinetic, oversized type, Bebas Neue, maximum impact
  - data_drift      → Futuristic/AI, neon on dark, Space Grotesk, digital world
  - soft_signal     → Warm/Intimate, earth tones, DM Serif Display, human connection
  - shadow_cut      → Dark Cinematic, high contrast, Barlow Condensed, drama

• Transitions:
  - crossfade → smooth dissolve through black (default, universal)
  - flash     → white camera-flash snap (dynamic, energetic)
  - zoom_punch → scale impact hard cut (aggressive, powerful)
  - wipe_left → horizontal clip-path sweep (editorial, clean)
  - glitch    → digital distortion + color aberration (futuristic, intense)

• Motion intensity:
  - calm      → Ken Burns max 1.04×, slow sine eases (elegant, relaxed)
  - medium    → Ken Burns max 1.08×, mixed eases (balanced, professional)
  - energetic → Ken Burns 1.10–1.15×, fast pans ±40px, elastic eases (dynamic, exciting)

• Text animation:
  - slide      → enter from below with opacity (clean, universal)
  - scale      → scale from 0.4→1 (logo-reveal, impact)
  - split      → individual words staggered (luxury editorial)
  - typewriter → clip-path reveal left-to-right (cinematic, narrative)

• Pipeline type:
  - hyperframes → highest quality (HTML + GSAP + Puppeteer rendering). Use for premium content.
  - ugc         → social media style with ffmpeg (faster, for UGC/organic content)

RESPONSE RULES:
1. Always respond in the SAME language the user writes in (Spanish or English).
2. Be warm, creative, and enthusiastic. You love video.
3. Ask clarifying questions if the vision is unclear (brand type? audience? mood?).
4. When you have enough info to make confident suggestions, include a JSON config block.
5. Keep responses concise (2-4 sentences max unless explaining options).

CONFIG EXTRACTION:
If you have confident parameter suggestions, end your response with this exact format:
```config
{
  "visual_style": "...",
  "transition_style": "...",
  "motion_intensity": "...",
  "text_animation": "...",
  "pipeline_type": "...",
  "creative_brief": "..."
}
```
Only include fields you're confident about. Omit the block entirely for greetings or vague requests.
"""


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest) -> ChatResponse:
    """Send a message to the AI assistant and get video config suggestions."""

    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    # Build context-awareness prefix if config was provided
    context_note = ""
    if req.context:
        style = req.context.get("visual_style", "")
        brief = req.context.get("creative_brief", "")
        brand = req.context.get("brand_slug", "")
        parts = []
        if brand:
            parts.append(f"selected brand: {brand}")
        if style:
            parts.append(f"current style: {style}")
        if brief:
            parts.append(f"current brief: {brief[:120]}")
        if parts:
            context_note = f"[Studio context — {', '.join(parts)}]\n\n"

    # Build messages for OpenAI
    openai_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in req.messages:
        role = msg.role if msg.role in ("user", "assistant") else "user"
        content = msg.content
        # Inject context note before the first user message
        if role == "user" and context_note:
            content = context_note + content
            context_note = ""  # only inject once
        openai_messages.append({"role": role, "content": content})

    response = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=openai_messages,  # type: ignore[arg-type]
        max_tokens=600,
        temperature=0.7,
    )

    raw = response.choices[0].message.content or ""

    # Extract config JSON block from response
    config_update: Optional[dict] = None
    config_match = re.search(r"```config\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if config_match:
        try:
            config_update = json.loads(config_match.group(1))
        except json.JSONDecodeError:
            config_update = None
        # Remove the config block from the visible message
        raw = re.sub(r"\n*```config\s*\{.*?\}\s*```", "", raw, flags=re.DOTALL).strip()

    return ChatResponse(message=raw, config_update=config_update)
