import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "@/features/auth/AuthContext";

export function AppLayout() {
  const { user, loading, logout } = useAuth();

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-10">
      <header className="border-b border-rule pb-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm tracking-[0.2em] text-ink-soft uppercase">
              Personal running laboratory
            </p>
            <Link to="/" className="font-display mt-3 inline-block text-5xl text-ink">
              PaceLab
            </Link>
          </div>
          <nav aria-label="Account" className="flex flex-wrap items-center gap-4 text-sm">
            {loading ? null : user ? (
              <>
                <NavLink
                  to="/activities"
                  className={({ isActive }) =>
                    isActive ? "text-moss-deep underline" : "text-ink-soft hover:text-ink"
                  }
                >
                  Activities
                </NavLink>
                <NavLink
                  to="/settings/account"
                  className={({ isActive }) =>
                    isActive ? "text-moss-deep underline" : "text-ink-soft hover:text-ink"
                  }
                >
                  Account
                </NavLink>
                <button
                  type="button"
                  onClick={() => {
                    void logout();
                  }}
                  className="text-ink-soft hover:text-ink"
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink
                  to="/login"
                  className={({ isActive }) =>
                    isActive ? "text-moss-deep underline" : "text-ink-soft hover:text-ink"
                  }
                >
                  Log in
                </NavLink>
                <NavLink
                  to="/register"
                  className={({ isActive }) =>
                    isActive ? "text-moss-deep underline" : "text-ink-soft hover:text-ink"
                  }
                >
                  Create account
                </NavLink>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex flex-1 flex-col gap-10 pt-10">
        <Outlet />
      </main>
      <footer className="mt-auto border-t border-rule pt-6 text-sm text-ink-soft">
        PaceLab · necessary session cookies only · Garmin integration uses official OAuth only
      </footer>
    </div>
  );
}
