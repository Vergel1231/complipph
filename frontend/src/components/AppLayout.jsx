import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  GaugeIcon, FileTextIcon, CalendarBlankIcon, ClockCounterClockwiseIcon,
  ChatCircleDotsIcon, GearSixIcon, SignOutIcon, ShieldCheckIcon, SparkleIcon,
} from "@phosphor-icons/react";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: GaugeIcon },
  { to: "/generate", label: "Generate Form", icon: SparkleIcon },
  { to: "/calendar", label: "Calendar", icon: CalendarBlankIcon },
  { to: "/history", label: "Filing History", icon: ClockCounterClockwiseIcon },
  { to: "/assistant", label: "AI Tax Assistant", icon: ChatCircleDotsIcon },
  { to: "/settings", label: "Settings", icon: GearSixIcon },
];

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-sand-100 flex">
      {/* Sidebar */}
      <aside
        className="w-64 shrink-0 bg-white border-r border-sand-300 hidden md:flex md:flex-col"
        data-testid="app-sidebar"
      >
        <div className="px-6 py-7 border-b border-sand-200">
          <NavLink to="/dashboard" className="flex items-center gap-2" data-testid="sidebar-logo-link">
            <div className="h-9 w-9 rounded-md bg-olive-600 grid place-items-center text-white font-display font-bold">B</div>
            <div>
              <div className="font-display font-bold text-olive-900 leading-none">BIR Filipino</div>
              <div className="text-[11px] tracking-[0.2em] uppercase text-terracotta-600 font-bold mt-1">Solo Pro</div>
            </div>
          </NavLink>
        </div>
        <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              data-testid={`nav-${n.label.toLowerCase().replace(/\s+/g, "-")}-link`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-olive-600 text-white"
                    : "text-sand-800 hover:bg-sand-200 hover:text-olive-900"
                }`
              }
            >
              <n.icon size={18} weight="duotone" />
              {n.label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              data-testid="nav-admin-link"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-terracotta-600 text-white"
                    : "text-terracotta-700 hover:bg-terracotta-50"
                }`
              }
            >
              <ShieldCheckIcon size={18} weight="duotone" />
              Admin
            </NavLink>
          )}
        </nav>
        <div className="px-4 py-4 border-t border-sand-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-9 w-9 rounded-full bg-sage-200 grid place-items-center font-display font-bold text-olive-800 text-sm">
              {user?.name?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-olive-900 truncate">{user?.name}</div>
              <div className="text-xs text-sand-600 truncate">{user?.email}</div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            data-testid="sidebar-logout-button"
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium border border-sand-300 hover:bg-sand-200 transition-colors"
          >
            <SignOutIcon size={16} /> Logout
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 bg-white border-b border-sand-300 z-30 px-4 py-3 flex items-center justify-between">
        <NavLink to="/dashboard" className="flex items-center gap-2 font-display font-bold text-olive-900">
          <div className="h-7 w-7 rounded-md bg-olive-600 grid place-items-center text-white text-sm">B</div>
          BIR Filipino
        </NavLink>
        <button onClick={handleLogout} className="text-sm text-olive-700 underline" data-testid="mobile-logout-button">Logout</button>
      </div>

      <main className="flex-1 md:px-12 px-4 md:py-10 py-20 max-w-[1400px] mx-auto w-full" data-testid="app-main-content">
        {children}
      </main>
    </div>
  );
}
