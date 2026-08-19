import { FormEvent, useEffect, useState } from "react";

import { Field, FormError, PrimaryButton } from "@/components/Form";
import {
  disconnectProvider,
  fetchProviderConnections,
  formatAuthError,
} from "@/lib/api";
import type { ProviderConnectionPublic } from "@/types/privacy";

export function ConnectedServicesPage() {
  const [connections, setConnections] = useState<ProviderConnectionPublic[]>([]);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshConnections() {
    setLoading(true);
    try {
      const result = await fetchProviderConnections();
      setConnections(result.items);
    } catch (caught) {
      setError(formatAuthError(caught));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshConnections();
  }, []);

  async function onDisconnect(event: FormEvent<HTMLFormElement>, provider: string) {
    event.preventDefault();
    setError(null);
    setStatus(null);
    try {
      const result = await disconnectProvider(provider, password);
      setPassword("");
      setStatus(result.message);
      await refreshConnections();
    } catch (caught) {
      setError(formatAuthError(caught));
    }
  }

  return (
    <section className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl">Connected services</h1>
        <p className="mt-4 leading-relaxed text-ink-soft">
          PaceLab does not ask for a Garmin or Strava username or password and does not scrape
          those sites. Upload FIT files on the Activities page to import runs from your watch.
          Live Garmin linking waits until the official developer programme accepts new apps.
          Strava OAuth is next.
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
        <p className="mt-2 text-sm text-ink-soft">
          Not connected. Official Strava OAuth is planned next and is not available yet.
        </p>
      </div>

      {loading ? <p className="text-ink-soft">Loading sync records…</p> : null}
      <FormError message={error} />
      {status ? (
        <p className="text-sm text-moss-deep" role="status">
          {status}
        </p>
      ) : null}

      {connections.length === 0 && !loading ? (
        <p className="text-ink-soft">No provider sync records on this account.</p>
      ) : null}

      {connections.map((connection) => (
        <form
          key={connection.provider}
          className="flex max-w-md flex-col gap-4 border border-rule px-4 py-4"
          onSubmit={(event) => void onDisconnect(event, connection.provider)}
        >
          <h2 className="font-display text-2xl">{connection.provider}</h2>
          <p className="text-sm text-ink-soft">
            Last PaceLab sync: {connection.last_sync_at ?? "never"}. Disconnecting does not
            delete your stored runs. Use Privacy → Delete running data if you want those
            gone too.
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
