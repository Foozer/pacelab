import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { HeartRateRangeForm } from "@/components/HeartRateRangeForm";
import {
  type HeartRateRange,
  readStoredHeartRateRange,
  storeHeartRateRange,
} from "@/lib/hrRange";

export function PreferencesPage() {
  const [range, setRange] = useState<HeartRateRange>(readStoredHeartRateRange);
  const [saved, setSaved] = useState(false);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (range.min >= range.max) {
      return;
    }
    storeHeartRateRange(range);
    setSaved(true);
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="font-display text-3xl">Preferences</h1>
        <p className="mt-4 leading-relaxed text-ink-soft">
          Choose the heart-rate window used for easy running and comparable-pace charts. This
          stays in this browser; PaceLab does not store a personal Zone 2 on the server.
        </p>
      </div>
      <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-4">
        <HeartRateRangeForm range={range} onChange={setRange} />
        <button type="submit" className="self-start bg-moss-deep px-4 py-2 text-paper hover:bg-moss">
          Save in this browser
        </button>
        {saved ? (
          <p className="text-sm text-moss-deep" role="status">
            Saved.{" "}
            <Link to="/easy-running" className="underline">
              Open Easy running
            </Link>
          </p>
        ) : null}
      </form>
    </section>
  );
}
