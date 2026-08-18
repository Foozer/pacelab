import type { InputHTMLAttributes, ReactNode } from "react";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: ReactNode;
}

export function Field({ label, hint, id, ...props }: FieldProps) {
  const fieldId = id ?? props.name;
  return (
    <label className="block">
      <span className="text-sm text-ink">{label}</span>
      <input
        id={fieldId}
        className="mt-2 w-full border border-rule bg-paper px-3 py-2 text-ink outline-none focus:border-moss"
        {...props}
      />
      {hint ? <span className="mt-2 block text-sm text-ink-soft">{hint}</span> : null}
    </label>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }
  return (
    <p className="rounded-sm border border-copper/40 bg-paper-2 px-4 py-3" role="alert">
      {message}
    </p>
  );
}

export function PrimaryButton({
  children,
  disabled,
}: {
  children: ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="bg-moss-deep px-4 py-2 text-paper hover:bg-moss disabled:opacity-60"
    >
      {children}
    </button>
  );
}
