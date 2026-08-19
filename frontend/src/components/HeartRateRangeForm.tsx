import { Field } from "@/components/Form";
import type { HeartRateRange } from "@/lib/hrRange";

export function HeartRateRangeForm({
  range,
  onChange,
  hint,
}: {
  range: HeartRateRange;
  onChange: (range: HeartRateRange) => void;
  hint?: string;
}) {
  return (
    <fieldset className="flex flex-col gap-4 sm:flex-row sm:items-end">
      <legend className="sr-only">Heart-rate range in beats per minute</legend>
      <Field
        label="From (bpm)"
        type="number"
        name="hr_min"
        min={40}
        max={219}
        value={range.min}
        onChange={(event) => onChange({ ...range, min: Number(event.target.value) })}
      />
      <Field
        label="To (bpm)"
        type="number"
        name="hr_max"
        min={41}
        max={220}
        value={range.max}
        onChange={(event) => onChange({ ...range, max: Number(event.target.value) })}
      />
      {hint ? <p className="text-sm text-ink-soft sm:pb-2">{hint}</p> : null}
    </fieldset>
  );
}
