export interface PipelineEvent {
  run_id: string;
  event_type: string;
  step_name: string | null;
  step_index: number | null;
  steps_total: number | null;
  message: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface PipelineRun {
  run_id: string;
  pipeline_type: string;
  status: "pending" | "running" | "paused" | "completed" | "failed";
  mode: "interactive" | "headless";
  current_step: string | null;
  steps_completed: number;
  steps_total: number | null;
  created_at: string;
}

export interface Brand {
  id?: number;
  name: string;
  slug: string;
  url?: string;
  tone_of_voice?: string;
  target_audience?: string;
  brand_values?: string[];
  style_notes?: string;
  character_anchor?: string;
  colors?: {
    primary?: string;
    secondary?: string;
    accent?: string;
    palette?: string[];
  };
  typography?: {
    heading_font?: string;
    body_font?: string;
  };
  preferred_voice_id?: string;
  created_at?: string;
}

export interface OutputAsset {
  id: number;
  run_id: string;
  asset_type: string;
  file_path: string;
  mime_type?: string;
  brand_id?: number;
  created_at: string;
}

export interface Script {
  run_id: string;
  brand_slug: string;
  title: string;
  hook: string;
  scenes: Scene[];
  cta: string;
  total_duration_seconds: number;
  target_platform: string;
  hashtags: string[];
  angle_type: string;
}

export interface Scene {
  index: number;
  title: string;
  duration_seconds: number;
  visual_description: string;
  speaker_text: string;
  on_screen_text: string | null;
}
