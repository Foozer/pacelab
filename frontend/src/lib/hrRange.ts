export const DEFAULT_HR_MIN = 140;
export const DEFAULT_HR_MAX = 150;

const STORAGE_KEY = "pacelab.easyHeartRateRange";

export type HeartRateRange = {
  min: number;
  max: number;
};

export function defaultHeartRateRange(): HeartRateRange {
  return { min: DEFAULT_HR_MIN, max: DEFAULT_HR_MAX };
}

export function readStoredHeartRateRange(): HeartRateRange {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaultHeartRateRange();
    }
    const parsed = JSON.parse(raw) as { min?: unknown; max?: unknown };
    const min = Number(parsed.min);
    const max = Number(parsed.max);
    if (!Number.isInteger(min) || !Number.isInteger(max) || min >= max) {
      return defaultHeartRateRange();
    }
    if (min < 40 || max > 220) {
      return defaultHeartRateRange();
    }
    return { min, max };
  } catch {
    return defaultHeartRateRange();
  }
}

export function storeHeartRateRange(range: HeartRateRange): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(range));
}
