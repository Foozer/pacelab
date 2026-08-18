import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/settings/account", label: "Account" },
  { to: "/settings/privacy", label: "Privacy" },
  { to: "/settings/connected-services", label: "Connected services" },
  { to: "/settings/preferences", label: "Preferences" },
];

export function SettingsLayout() {
  return (
    <div className="flex flex-col gap-8 sm:flex-row">
      <nav aria-label="Settings" className="sm:w-48">
        <p className="text-xs tracking-wide text-ink-soft uppercase">Settings</p>
        <ul className="mt-3 flex flex-col gap-2">
          {links.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) =>
                  isActive ? "text-moss-deep underline" : "text-ink-soft hover:text-ink"
                }
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
