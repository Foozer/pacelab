interface PlaceholderSettingsPageProps {
  title: string;
  body: string;
}

export function PlaceholderSettingsPage({ title, body }: PlaceholderSettingsPageProps) {
  return (
    <section>
      <h1 className="font-display text-3xl">{title}</h1>
      <p className="mt-4 leading-relaxed text-ink-soft">{body}</p>
    </section>
  );
}
