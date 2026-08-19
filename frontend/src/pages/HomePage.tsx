import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchHealth } from "@/lib/api";
import { useAuth } from "@/features/auth/AuthContext";
import type { HealthResponse } from "@/types/health";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; health: HealthResponse }
  | { status: "error"; message: string };

export function HomePage() {
  const { user } = useAuth();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((health) => {
        if (!cancelled) {
          setState({ status: "ready", health });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Unable to reach the API";
          setState({ status: "error", message });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <section>
        <h1 className="font-display text-3xl">How is my running going?</h1>
        <p className="mt-4 max-w-xl text-lg leading-relaxed text-ink-soft">
          Understand whether your fitness is actually improving — pace relative to heart rate,
          easy running, and long-term trends. Not another copy of Garmin Connect.
        </p>
        {user ? (
          <p className="mt-6 text-ink">
            Signed in as {user.email}. Review your{" "}
            <Link to="/activities" className="text-moss-deep underline">
              activities
            </Link>{" "}
            or manage your{" "}
            <Link to="/settings/account" className="text-moss-deep underline">
              account
            </Link>
            .
          </p>
        ) : (
          <p className="mt-6 text-ink">
            <Link to="/register" className="text-moss-deep underline">
              Create an account
            </Link>{" "}
            or{" "}
            <Link to="/login" className="text-moss-deep underline">
              log in
            </Link>{" "}
            to start using PaceLab.
          </p>
        )}
      </section>

      <section aria-labelledby="stack-status">
        <h2 id="stack-status" className="font-display text-2xl">
          Foundation status
        </h2>
        <p className="mt-2 text-ink-soft">
          Phase 3 adds activity import and a simple history list. Dashboard charts come next.
        </p>
        <StatusPanel state={state} />
      </section>
    </>
  );
}

function StatusPanel({ state }: { state: LoadState }) {
  if (state.status === "loading") {
    return (
      <p className="mt-6 rounded-sm border border-rule bg-paper-2 px-4 py-3" role="status">
        Checking API health…
      </p>
    );
  }

  if (state.status === "error") {
    return (
      <p className="mt-6 rounded-sm border border-copper/40 bg-paper-2 px-4 py-3" role="alert">
        The API did not respond. {state.message}. Confirm the backend is running
        on port 8000, then refresh. In WSL use{" "}
        <code className="font-mono text-sm">docker compose up</code>
        {", "}not <code className="font-mono text-sm">docker-compose</code>.
      </p>
    );
  }

  const healthy = state.health.status === "ok" && state.health.database === "connected";

  return (
    <dl className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
      <StatusCard label="API" value={healthy ? "Reachable" : "Unhealthy"} ok={healthy} />
      <StatusCard
        label="PostgreSQL"
        value={state.health.database === "connected" ? "Connected" : "Disconnected"}
        ok={state.health.database === "connected"}
      />
      <StatusCard label="Version" value={state.health.version} ok={healthy} />
    </dl>
  );
}

function StatusCard({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="border border-rule bg-paper-2 px-4 py-4">
      <dt className="text-xs tracking-wide text-ink-soft uppercase">{label}</dt>
      <dd className={`font-display mt-2 text-xl ${ok ? "text-moss-deep" : "text-copper"}`}>
        {value}
      </dd>
    </div>
  );
}
