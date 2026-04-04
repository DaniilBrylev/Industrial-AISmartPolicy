import { NavLink, Outlet } from "react-router-dom";

type NavItem = { to: string; label: string; end?: boolean };

const links: NavItem[] = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/departments", label: "Подразделения" },
  { to: "/questionnaires", label: "Анкеты" },
  { to: "/policies", label: "Политики" },
  { to: "/versions", label: "Версии / история" },
];

export function Layout() {
  return (
    <div className="layout">
      <nav className="layoutNav" aria-label="Основное меню">
        <div className="layoutNavTitle">
          Политика ИБ
          <br />
          <span style={{ fontWeight: 400, fontSize: "11px", opacity: 0.9 }}>
            промышленное предприятие
          </span>
        </div>
        {links.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end === true}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="layoutMain">
        <Outlet />
      </div>
    </div>
  );
}
