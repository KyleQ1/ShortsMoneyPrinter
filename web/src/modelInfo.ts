import type { ModelInfo, Quality } from "./types";

export type ProviderMode = "local" | "remote";

export function modelInfoMap(models: ModelInfo[]): Record<Quality, ModelInfo> {
  return Object.fromEntries(models.map((model) => [model.quality, model]));
}

export function canonicalQuality(models: ModelInfo[], quality: Quality): Quality | null {
  const direct = models.find((model) => model.quality === quality);
  if (direct) return direct.quality;
  const alias = models.find((model) => model.aliases.includes(quality));
  return alias?.quality || null;
}

export function modelOptionsForMode(models: ModelInfo[], providerMode: ProviderMode): ModelInfo[] {
  return models.filter((model) => model.provider_mode === providerMode);
}

export function providerModeForQuality(models: ModelInfo[], quality: Quality): ProviderMode {
  return modelInfoMap(models)[quality]?.provider_mode || "local";
}

export function defaultQualityForMode(models: ModelInfo[], providerMode: ProviderMode): Quality {
  return (
    models.find((model) => model.provider_mode === providerMode && model.default_for_mode)
    || models.find((model) => model.provider_mode === providerMode)
    || models[0]
  )?.quality || "local";
}

export function isLocalQuality(models: ModelInfo[], quality: Quality): boolean {
  return providerModeForQuality(models, quality) === "local";
}
