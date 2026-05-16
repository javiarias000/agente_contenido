from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from openai import AsyncOpenAI

from api.config import settings
from api.events import EventBus
from skills import BaseSkill, SkillResult

PLATFORM_DIMS: dict[str, tuple[int, int]] = {
    "tiktok": (1080, 1920),
    "instagram_reel": (1080, 1920),
    "youtube_short": (1080, 1920),
    "instagram_square": (1080, 1080),
}

VISUAL_STYLES = {
    "swiss_pulse": {
        "desc": "Clinical precision — clean grid, strong type, SaaS/tech feel",
        "bg": "#0a0a0a", "primary": "#ffffff", "accent": "#2563eb", "secondary": "#6b7280",
        "font": "Inter", "ease_sig": "power3.out / expo.out",
    },
    "velvet_standard": {
        "desc": "Premium timeless — rich dark, gold accents, luxury brands",
        "bg": "#0d0d0d", "primary": "#f5f0e8", "accent": "#c9a84c", "secondary": "#8a8078",
        "font": "Cormorant Garamond", "ease_sig": "sine.inOut / power2.out",
    },
    "maximalist_type": {
        "desc": "Loud kinetic — oversized type fills frame, high energy social",
        "bg": "#111111", "primary": "#ffffff", "accent": "#ff2d55", "secondary": "#ffcc00",
        "font": "Bebas Neue", "ease_sig": "back.out(1.7) / elastic.out(1, 0.5)",
    },
    "data_drift": {
        "desc": "Futuristic AI/ML — neon on dark, data-viz aesthetic",
        "bg": "#050510", "primary": "#e0e8ff", "accent": "#00d4ff", "secondary": "#7c3aed",
        "font": "Space Grotesk", "ease_sig": "expo.out / circ.out",
    },
    "soft_signal": {
        "desc": "Intimate wellness — warm tones, soft motion, lifestyle/beauty",
        "bg": "#1a1410", "primary": "#f5ede0", "accent": "#e8836a", "secondary": "#b8a090",
        "font": "DM Serif Display", "ease_sig": "power2.out / sine.out",
    },
    "shadow_cut": {
        "desc": "Dark cinematic — high contrast, dramatic reveals, editorial",
        "bg": "#000000", "primary": "#f0f0f0", "accent": "#e5432a", "secondary": "#444444",
        "font": "Barlow Condensed", "ease_sig": "power4.out / expo.in",
    },
}

# Composer system prompt — includes all HyperFrames rules GPT-4o must follow
COMPOSER_SYSTEM = """You are an expert HyperFrames video composition author. You output ONLY a complete HTML file — no markdown, no code blocks, no explanations.

## COMPOSITION STRUCTURE (mandatory)

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
  <div data-composition-id="root" data-width="{W}" data-height="{H}">
    <!-- clips and captions here -->
  </div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    var tl = gsap.timeline({ paused: true });
    // tweens...
    window.__timelines = { "root": tl };
  </script>
</body>
</html>
```

## CLIPS
Every scene is a timed element with these REQUIRED attributes:
- `id="sN"` (unique)
- `data-start="N"` (seconds, float)
- `data-duration="N"` (seconds, float)
- `data-track-index="0"` (same-track clips cannot overlap)

Scene content container MUST use:
```css
.scene-content {
  width: 100%; height: 100%;
  padding: 120px 80px;
  display: flex; flex-direction: column;
  justify-content: center; gap: 24px;
  box-sizing: border-box;
}
```
NEVER use `position: absolute` on `.scene-content`. Only on decorative elements.

## ANIMATIONS (GSAP — non-negotiable rules)
1. `gsap.timeline({ paused: true })` — ALWAYS paused, NEVER play/seek manually
2. Register: `window.__timelines = { "root": tl }` — EXACTLY this key
3. NEVER use `Math.random()`, `Date.now()`, or time-based logic
4. NEVER use `repeat: -1`
5. Build timeline synchronously — NO `async/await`, `setTimeout`, or Promises
6. ALL elements MUST animate IN with `tl.from()` — no element appears fully-formed
7. NO exit animations except final scene — transitions handle exits between scenes
8. Offset first animation 0.1–0.3s (NOT at t=0)
9. Vary eases — use at least 3 different eases per scene
10. Use `tl.set(selector, vars, timePosition)` inside the timeline for late-appearing elements — NEVER `gsap.set()` on elements from later scenes

## SCENE TRANSITIONS (mandatory for multi-scene compositions)
Place a crossfade overlay between every pair of scenes:
```html
<div id="fade-N" style="position:absolute;top:0;left:0;width:100%;height:100%;background:#000;opacity:0;z-index:50;pointer-events:none"></div>
```
```js
// Transition from scene N to N+1 at scene N's end minus 0.4s:
tl.to("#fade-N", {opacity:1, duration:0.3, ease:"power2.inOut"}, sceneNEnd - 0.4);
tl.to("#fade-N", {opacity:0, duration:0.3, ease:"power2.inOut"}, sceneNEnd + 0.1);
```

## CAPTIONS (you will receive pre-computed groups)
Caption groups are positioned OUTSIDE clips, as siblings within the composition:
```html
<!-- All captions start hidden, timeline controls visibility -->
<div id="cg-0" style="position:absolute;bottom:380px;left:0;right:0;text-align:center;opacity:0;visibility:hidden;z-index:100">
  <div class="cap-text">Word1 Word2 Word3</div>
</div>
```
Caption font: 68–80px, font-weight 800, color white, text-shadow for legibility.
For each group (gi = group index, group.start/end in seconds):
```js
tl.set("#cg-"+gi, {opacity:1, visibility:"visible"}, group.start);
tl.from("#cg-"+gi, {scale:0.85, opacity:0, duration:0.12, ease:"back.out(1.7)"}, group.start);
tl.to("#cg-"+gi, {opacity:0, scale:0.95, duration:0.12, ease:"power2.in"}, group.end - 0.12);
tl.set("#cg-"+gi, {opacity:0, visibility:"hidden"}, group.end);
```
One accent-colored span for each individual word within the group:
```html
<div class="cap-text"><span class="cw" id="cw-0-0">Word1</span> <span class="cw" id="cw-0-1">Word2</span></div>
```
```js
// Highlight each word at its timestamp:
tl.to("#cw-0-0", {color:"VAR_ACCENT", scale:1.08, duration:0.08, ease:"power3.out"}, word.start);
tl.to("#cw-0-0", {color:"#ffffff", scale:1, duration:0.08, ease:"power2.in"}, word.end);
```

## VISUAL QUALITY
- Three layers minimum per scene: background treatment, foreground content, accent elements
- Background is NEVER a plain solid — use radial gradients, oversized faded type, subtle geometric shapes
- Hero text: 80–120px. Fill the frame (60–80% width).
- Use CSS custom properties for brand colors
- Structural elements: hairline rules, dividers — they animate well with `scaleX: 0 → 1`
- Never a single text block floating in space — add supporting elements (stat, badge, label, divider)

## OUTPUT
Return ONLY the complete HTML document. First character must be `<`, last must be `>`.
"""


async def _get_audio_duration(path: str) -> float:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        return float(stdout.decode().strip())
    except Exception:
        return 3.0


def _group_words(words: list[dict], max_per_group: int = 4) -> list[dict]:
    """Group transcript words into caption chunks (3–4 per group, break on pauses)."""
    if not words:
        return []
    groups: list[dict] = []
    current: list[dict] = []

    for i, w in enumerate(words):
        current.append(w)
        gap = (words[i + 1]["start"] - w["end"]) if i + 1 < len(words) else 999
        is_sentence_end = w["word"].endswith((".", "!", "?", ",", ";", ":"))

        if len(current) >= max_per_group or gap > 0.4 or is_sentence_end:
            groups.append({
                "id": f"cg-{len(groups)}",
                "text": " ".join(c["word"] for c in current),
                "start": current[0]["start"],
                "end": current[-1]["end"] + 0.05,
                "words": [{"id": f"cw-{len(groups)}-{j}", **c} for j, c in enumerate(current)],
            })
            current = []

    if current:
        groups.append({
            "id": f"cg-{len(groups)}",
            "text": " ".join(c["word"] for c in current),
            "start": current[0]["start"],
            "end": current[-1]["end"] + 0.05,
            "words": [{"id": f"cw-{len(groups)}-{j}", **c} for j, c in enumerate(current)],
        })

    return groups


class HyperFramesComposer(BaseSkill):
    """Uses GPT-4o to generate a brand-aware HyperFrames HTML composition with animated captions."""
    skill_name = "hyperframes_composer"

    def __init__(self, event_bus: EventBus, run_id: str, step_index: int = 0):
        super().__init__(event_bus, run_id, step_index)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, inputs: dict[str, Any], interactive: bool = False) -> SkillResult:
        script: dict = inputs["script"]
        profile: dict = inputs.get("profile", {})
        audio_paths: list[str] = inputs.get("audio_paths", [])
        transcript_words: list[dict] = inputs.get("transcript_words", [])
        platform: str = inputs.get("platform", "tiktok")
        visual_style_key: str = inputs.get("visual_style", "swiss_pulse")

        await self.emit("step_start", "Generando composición HTML con HyperFrames...")

        width, height = PLATFORM_DIMS.get(platform, (1080, 1920))
        style = VISUAL_STYLES.get(visual_style_key, VISUAL_STYLES["swiss_pulse"])

        # Override style defaults with brand colors if available
        brand_colors: dict = profile.get("colors") or {}
        accent = brand_colors.get("accent") or brand_colors.get("primary") or style["accent"]
        bg = brand_colors.get("background") or brand_colors.get("bg") or style["bg"]
        primary = brand_colors.get("text") or brand_colors.get("foreground") or style["primary"]
        secondary = brand_colors.get("secondary") or style["secondary"]

        # Calculate scene timings from audio durations
        scenes = script.get("scenes", [])
        cursor = 0.0
        timed_scenes = []
        for scene in scenes:
            idx = scene.get("index", len(timed_scenes))
            dur = 3.0
            if idx < len(audio_paths) and audio_paths[idx] and os.path.exists(audio_paths[idx]):
                dur = await _get_audio_duration(audio_paths[idx])
            timed_scenes.append({**scene, "start": round(cursor, 3), "duration": round(dur, 3)})
            cursor += dur
        total_duration = round(cursor, 3)

        # Group transcript words into caption chunks
        caption_groups = _group_words(transcript_words)

        await self.emit("progress", f"Composición: {len(timed_scenes)} escenas, {len(caption_groups)} grupos de subtítulos, {total_duration:.1f}s")

        # Build user message
        user_data = {
            "brand": {
                "name": profile.get("name", profile.get("slug", "Brand")),
                "colors": {"bg": bg, "primary": primary, "accent": accent, "secondary": secondary},
                "tone": profile.get("tone_of_voice", ""),
                "audience": profile.get("target_audience", ""),
            },
            "platform": {"name": platform, "width": width, "height": height},
            "visual_style": style["desc"],
            "total_duration": total_duration,
            "scenes": timed_scenes,
            "caption_groups": caption_groups,
        }

        system = COMPOSER_SYSTEM.replace("{W}", str(width)).replace("{H}", str(height))
        user_msg = (
            "Generate the complete HyperFrames HTML composition for this video.\n\n"
            + json.dumps(user_data, ensure_ascii=False, indent=2)
        )

        await self.emit("progress", "Llamando a GPT-4o para generar HTML...")

        resp = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=8000,
        )
        html = resp.choices[0].message.content or ""

        # Strip markdown code fences if present
        if html.startswith("```"):
            lines = html.split("\n")
            html = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        if not html.strip().startswith("<"):
            raise ValueError("GPT-4o did not return valid HTML. Output starts with: " + html[:80])

        # Save to outputs/compositions/{run_id}/
        comp_dir = os.path.join(settings.outputs_dir, "compositions", self.run_id)
        os.makedirs(comp_dir, exist_ok=True)
        comp_path = os.path.join(comp_dir, "index.html")
        with open(comp_path, "w", encoding="utf-8") as f:
            f.write(html)

        await self.emit(
            "step_complete",
            "Composición HTML generada",
            data={"composition_path": comp_path, "total_duration": total_duration},
        )
        return SkillResult(
            status="completed",
            outputs={"composition_path": comp_path, "total_duration": total_duration},
        )
