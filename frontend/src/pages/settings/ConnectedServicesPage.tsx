import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Field, FormError, PrimaryButton } from "@/components/Form";
import {
  disconnectProvider,
  fetchProviderConnections,
  fetchStravaStatus,
  formatAuthError,
  stravaConnectUrl,
  syncStravaActivities,
} from "@/lib/api";
import type { ProviderConnectionPublic } from "@/types/privacy";
import type { StravaStatus } from "@/types/strava";

export function ConnectedServicesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [connections, setConnections] = useState<ProviderConnectionPublic[]>([]);
  const [strava, setStrava] = useState<StravaStatus | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const [result, stravaStatus] = await Promise.all([
        fetchProviderConnections(),
        fetchStravaStatus(),
      ]);
      setConnections(result.items.filter((item) => item.provider !== "strava"));
      setStrava(stravaStatus);
    } catch (caught) {
      setError(formatAuthError(caught));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    const flag = searchParams.get("strava");
    if (!flag) {
      return;
    }
    if (flag === "connected") {
      setStatus("Connected to Strava. Use Sync now to pull recent runs.");
    } else if (flag === "denied") {
      setError("Strava access was not granted.");
    }
    const next = new URLSearchParams(searchParams);
    next.delete("strava");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  async function onDisconnect(event: FormEvent<HTMLFormElement>, provider: string) {
    event.preventDefault();
    setError(null);
    setStatus(null);
    try {
      const result = await disconnectProvider(provider, password);
      setPassword("");
      setStatus(result.message);
      await refresh();
    } catch (caught) {
      setError(formatAuthError(caught));
    }
  }

  async function onStravaSync() {
    setError(null);
    setStatus(null);
    setSyncing(true);
    try {
      const result = await syncStravaActivities();
      setStatus(
        `Imported ${result.created} new from Strava, updated ${result.updated}. ${result.total} activities in this pull.`,
      );
      await refresh();
    } catch (caught) {
      setError(formatAuthError(caught));
    } finally {
      setSyncing(false);
    }
  }

  const otherConnections = connections;

  return (
    <section className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl">Connected services</h1>
        <p className="mt-4 leading-relaxed text-ink-soft">
          PaceLab does not ask for a Garmin or Strava username or password and does not scrape
          those sites. Connecting Strava is a Strava connection, not a Garmin connection. Upload
          FIT files on the Activities page to import a file from your watch. PaceLab is not a
          Strava or Garmin partner.
        </p>
      </div>

      <div className="border border-rule bg-paper-2 px-4 py-4">
        <h2 className="font-display text-2xl">FIT file import</h2>
        <p className="mt-2 text-sm text-ink-soft">
          Available now. Upload <code className="font-mono">.fit</code> files from Garmin Connect
          or your device. This is a file import, not a live Garmin connection. Location data in
          the file is discarded.
        </p>
      </div>

      <div className="border border-rule bg-paper-2 px-4 py-4">
        <h2 className="font-display text-2xl">Garmin Connect</h2>
        <p className="mt-2 text-sm text-ink-soft">
          Live connect is not available. Official OAuth is deferred. Do not enter a Garmin
          password here.
        </p>
      </div>

      <div className="border border-rule bg-paper-2 px-4 py-4">
        <h2 className="font-display text-2xl">Strava</h2>
        {strava === null ? (
          <p className="mt-2 text-sm text-ink-soft">Checking Strava…</p>
        ) : !strava.configured ? (
          <p className="mt-2 text-sm text-ink-soft">Strava is not configured on this server.</p>
        ) : strava.needs_reconnect ? (
          <p className="mt-2 text-sm text-ink-soft">
            Strava access expired. Connect again. This is not a Garmin link.
          </p>
        ) : strava.connected ? (
          <p className="mt-2 text-sm text-ink-soft">
            Connected to Strava. Last sync: {strava.last_sync_at ?? "never"}. Syncing pulls your
            recent Strava activities into PaceLab. The same run uploaded as a FIT file is stored
            separately.
          </p>
        ) : (
          <p className="mt-2 text-sm text-ink-soft">
            Not connected. Connecting asks Strava for permission to read your activities. PaceLab
            does not see your Strava password.
          </p>
        )}
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          {strava?.configured && !strava.connected ? (
            <a
              className="inline-block bg-moss-deep px-4 py-2 text-center text-paper hover:bg-moss"
              href={stravaConnectUrl()}
            >
              Connect Strava
            </a>
          ) : null}
          {strava?.configured && strava.needs_reconnect ? (
            <a
              className="inline-block bg-moss-deep px-4 py-2 text-center text-paper hover:bg-moss"
              href={stravaConnectUrl()}
            >
              Connect Strava again
            </a>
          ) : null}
          {strava?.connected && !strava.needs_reconnect ? (
            <button
              type="button"
              className="bg-moss-deep px-4 py-2 text-paper hover:bg-moss disabled:opacity-60"
              disabled={syncing}
              onClick={() => void onStravaSync()}
            >
              {syncing ? "Syncing…" : "Sync now"}
            </button>
          ) : null}
        </div>
      </div>

      {loading ? <p className="text-ink-soft">Loading sync records…</p> : null}
      <FormError message={error} />
      {status ? (
        <p className="text-sm text-moss-deep" role="status">
          {status}
        </p>
      ) : null}

      {strava?.connected ? (
        <form
          className="flex max-w-md flex-col gap-4 border border-rule px-4 py-4"
          onSubmit={(event) => void onDisconnect(event, "strava")}
        >
          <h2 className="font-display text-2xl">Disconnect Strava</h2>
          <p className="text-sm text-ink-soft">
            This revokes PaceLab’s Strava access and keeps your imported runs. It is not a Garmin
            disconnect. Use Privacy → Delete running data if you want those runs gone too.
          </p>
          <Field
            label="Current password"
            name="disconnect_password_strava"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <PrimaryButton>Disconnect Strava</PrimaryButton>
        </form>
      ) : null}

      {otherConnections.length === 0 && !loading && !strava?.connected ? (
        <p className="text-ink-soft">No other provider sync records on this account.</p>
      ) : null}

      {otherConnections.map((connection) => (
        <form
          key={connection.provider}
          className="flex max-w-md flex-col gap-4 border border-rule px-4 py-4"
          onSubmit={(event) => void onDisconnect(event, connection.provider)}
        >
          <h2 className="font-display text-2xl">{connection.provider}</h2>
          <p className="text-sm text-ink-soft">
            Last PaceLab sync: {connection.last_sync_at ?? "never"}. Disconnecting does not
            delete your stored runs. Use Privacy → Delete running data if you want those gone
            too.
          </p>
          <Field
            label="Current password"
            name={`disconnect_password_${connection.provider}`}
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <PrimaryButton>Disconnect</PrimaryButton>
        </form>
      ))}
    </section>
  );
}
