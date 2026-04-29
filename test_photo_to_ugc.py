"""
Test: Photo-to-UGC complete pipeline with real Mi Idea product photo
Claude Code orchestrates: PhotoAnalyzer → ScriptGenerator → KlingVideoGenerator → VoiceGenerator → Assembler
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, ".")

from api.config import settings
from api.events import EventBus, PipelineEvent
from pipelines.ugc_pipeline import UGCPipeline
import uuid


class OrchestratorEventBus(EventBus):
    """Event bus with clean output."""
    def __init__(self):
        self.events = []

    async def emit(self, event: PipelineEvent):
        self.events.append(event.to_dict())
        if event.event_type in ["step_start", "step_complete", "progress", "pipeline_failed"]:
            print(f"[{event.event_type:20}] {event.message}")
            if event.data and "error" in str(event.data):
                print(f"       {event.data}")


async def main():
    print("=" * 80)
    print("🎬 PHOTO-TO-UGC PIPELINE TEST")
    print("=" * 80)
    print()

    # Use the product photo
    photo_path = "/home/ubuntu/agente_contenido/outputs/uploads/test_mi_idea.jpg"

    if not os.path.exists(photo_path):
        print(f"❌ Photo not found: {photo_path}")
        return

    print(f"📸 Photo: {Path(photo_path).name} ({os.path.getsize(photo_path) / (1024 * 1024):.1f}MB)")
    print()

    run_id = f"photo_ugc_{uuid.uuid4().hex[:8]}"
    event_bus = OrchestratorEventBus()

    # Pipeline inputs
    inputs = {
        "brand_slug": "mi-idea",
        "user_photo_path": photo_path,
        "angle_type": "sales",
        "platform": "tiktok",
        "target_duration": 30,
        "character_description": "Diseñador creativo mostrando el producto de corte láser",
    }

    print(f"📋 RUN ID: {run_id}")
    print(f"🎯 Brand: mi-idea")
    print(f"📸 Using uploaded photo")
    print(f"🎬 Pipeline will:")
    print(f"   1. Analyze photo with GPT-4o Vision")
    print(f"   2. Generate product-specific UGC script")
    print(f"   3. Generate video with Kling AI (will skip if no fal_api_key)")
    print(f"   4. Synthesize voice")
    print(f"   5. Generate subtitles")
    print(f"   6. Assemble final video")
    print()

    try:
        pipeline = UGCPipeline(event_bus, run_id, db_session=None)
        result = await pipeline.execute(inputs)

        print()
        print("=" * 80)
        print("📊 RESULTADO")
        print("=" * 80)
        print()

        if result.get("status") == "completed":
            print("✅ PIPELINE COMPLETADO EXITOSAMENTE")
            print()

            outputs = result.get("outputs", {})

            # Photo analysis
            product_name = outputs.get("product_name", "Producto")
            print(f"📸 Análisis de foto: {product_name}")
            print()

            # Script
            script = outputs.get("script", {})
            if script:
                print(f"📝 Script generado:")
                print(f"   - Título: {script.get('title', 'N/A')}")
                print(f"   - Escenas: {len(script.get('scenes', []))}")
                print(f"   - Hook: {script.get('hook', '')[:60]}...")
                print()

            # Video/Images
            video_paths = outputs.get("video_paths", [])
            image_paths = outputs.get("image_paths", [])

            if video_paths:
                print(f"🎥 Videos Kling generados: {len(video_paths)}")
                for i, vp in enumerate(video_paths):
                    if os.path.exists(vp):
                        size_mb = os.path.getsize(vp) / (1024 * 1024)
                        print(f"   - Clip {i+1}: {size_mb:.1f}MB ✅")
                print()

            # Audio
            audio_paths = outputs.get("audio_paths", [])
            if audio_paths:
                print(f"🔊 Audio generado: {len(audio_paths)} escenas")
                full_voiceover = outputs.get("full_voiceover_path", "")
                if full_voiceover and os.path.exists(full_voiceover):
                    size_mb = os.path.getsize(full_voiceover) / (1024 * 1024)
                    print(f"   - Full voiceover: {size_mb:.1f}MB ✅")
                print()

            # Final video
            final_video = outputs.get("final_video_path", "")
            if final_video and os.path.exists(final_video):
                size_mb = os.path.getsize(final_video) / (1024 * 1024)
                print(f"🎬 VIDEO FINAL LISTO:")
                print(f"   - {Path(final_video).name}")
                print(f"   - Tamaño: {size_mb:.1f}MB")
                print(f"   - Ruta: {final_video}")
                print()
                print("   ✅ LISTO PARA PUBLICAR EN TIKTOK/INSTAGRAM")
            elif not video_paths:
                print(f"⚠️  Video Kling no se generó (requiere fal_api_key válido)")
                if image_paths:
                    print(f"   Usando imágenes generadas en su lugar")
                    final_video = outputs.get("final_video_path", "")
                    if final_video:
                        print(f"   Video: {final_video}")

        else:
            print(f"❌ PIPELINE FALLÓ")
            print(f"Status: {result.get('status')}")
            print(f"Error: {result.get('error')}")
            print()
            print("Eventos procesados:")
            for evt in event_bus.events[-10:]:
                if "error" in str(evt.get("data", {})).lower() or evt["event_type"] == "pipeline_failed":
                    print(f"  [{evt['event_type']}] {evt['message']}")

        print()
        print("=" * 80)
        print(f"📈 Total eventos: {len(event_bus.events)}")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error ejecutando pipeline: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
