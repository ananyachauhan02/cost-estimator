/**
 * platformSettings.ts
 * Shared utility for reading/writing platform-level defaults
 * (discount %, inflation %) persisted in localStorage.
 */

const SETTINGS_KEY = "businessnext_platform_settings";

export interface PlatformSettings {
  defaultDiscount: number;  // percent, e.g. 10
  defaultInflation: number; // percent, e.g. 5
}

const DEFAULTS: PlatformSettings = {
  defaultDiscount: 10,
  defaultInflation: 5,
};

export function getPlatformSettings(): PlatformSettings {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULTS;
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return DEFAULTS;
  }
}

export function savePlatformSettings(s: PlatformSettings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}
