import type { ModelInfo, Quality } from "./types";

export const modelInfo: Record<Quality, ModelInfo> = {
  local: {
    title: "Wan 2.2 TI2V-5B",
    detail: "Default local model path. Runs through your own Wan command and keeps generation on your machine.",
    cost: "$0 provider cost inside this app. Your local hardware, electricity, and setup time still apply.",
  },
  budget: {
    title: "Replicate Seedance 1.5 Pro",
    detail:
      "BYO Replicate key required. 480p image-to-video from a keyframe. It does not take direct video input, so source motion may be less faithful.",
    cost: "$0.013/sec without generated audio. Around $0.13 for 10s or $0.39 for 30s.",
  },
  standard: {
    title: "Replicate Seedance 2.0 Fast",
    detail:
      "BYO Replicate key required. 480p video-to-video. Default for faithful source motion and fastest paid cloud mode.",
    cost: "$0.08/sec using Replicate's video-input tier. Around $0.80 for 10s or $2.40 for 30s.",
  },
  premium: {
    title: "Replicate Seedance 2.0",
    detail:
      "BYO Replicate key required. 720p video-to-video. Highest cloud quality and most expensive option.",
    cost: "$0.22/sec using Replicate's video-input tier. Around $2.20 for 10s or $6.60 for 30s.",
  },
};
