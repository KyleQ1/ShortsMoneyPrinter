export type Quality = "budget" | "standard" | "premium" | "local";
export type Language = "auto" | "en" | "zh" | "hi" | "es" | "fr" | "de" | "ja" | "ko" | "pt";
export type AudioMode = "source" | "tts" | "none";
export type RunStatus = "planned" | "running" | "done" | "failed";
export type BlockStatus = "planned" | "generating" | "done" | "failed" | "skipped";

export type StyleOption = {
  key: string;
  label: string;
  kids: boolean;
};

export type RemixRequest = {
  source: string;
  style: string;
  prompt: string | null;
  video_subject_prompt: string | null;
  video_script_prompt: string | null;
  language: Language;
  audio_mode: AudioMode;
  tts_voice: string | null;
  quality: Quality;
  max_cost: number;
  captions: boolean;
  max_total_seconds: number | null;
  wan_command: string | null;
};

export type BlockPlan = {
  index: number;
  start: number;
  end: number;
  duration: number;
  mode: string;
  status: BlockStatus;
  ref_video: string;
  keyframe: string;
  prompt_path: string;
  prompt: string;
  generated_path: string;
  estimated_cost: number;
  error: string | null;
};

export type RunPlan = {
  run_id: string;
  created_at: string;
  status: RunStatus;
  source: string;
  source_platform: string;
  source_title: string | null;
  source_path: string;
  audio_path: string | null;
  run_dir: string;
  style: string;
  user_prompt: string | null;
  video_subject_prompt: string | null;
  video_script_prompt: string | null;
  language: Language;
  audio_mode: AudioMode;
  tts_voice: string | null;
  quality: Quality;
  provider: string;
  model_id: string;
  model_label: string;
  mode: string;
  resolution: string;
  width: number;
  height: number;
  original_duration: number;
  duration: number;
  aspect_ratio: string;
  has_audio: boolean;
  captions: boolean;
  captions_path: string | null;
  max_cost: number | null;
  wan_command: string | null;
  estimated_cost: number;
  block_count: number;
  blocks: BlockPlan[];
  final_path: string | null;
  error: string | null;
};

export type PreflightStatus = {
  ffmpeg: boolean;
  ffprobe: boolean;
  yt_dlp: boolean;
  endpoint: string;
  replicate_token: boolean;
  replicate_package: boolean;
  fal_token: boolean;
  fal_package: boolean;
};

export type ModelInfo = {
  title: string;
  detail: string;
  cost: string;
};
