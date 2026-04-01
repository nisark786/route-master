import { useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { Menu, X, LogOut, Truck, } from "lucide-react";

import { useLogoutMutation } from "../features/auth/authApi";
import { logout as logoutAction } from "../features/auth/authSlice";
import {
  COMPANY_ADMIN_NAV_CATEGORIES,
  getCompanyAdminActiveCategory,
} from "../routes/companyAdminNavigation";

const NAV_ITEMS_BY_ROLE = {
  SUPER_ADMIN: [
    { to: "/admin/dashboard", label: "Dashboard" },
    { to: "/admin/companies", label: "Companies" },
    { to: "/admin/subscriptions", label: "Subscription" },
    { to: "/admin/chat", label: "Chat" },
  ],
  COMPANY_ADMIN: COMPANY_ADMIN_NAV_CATEGORIES.map((category) => ({
    to: category.items[0].to,
    label: category.label,
    categoryId: category.id,
  })),
  DRIVER: [{ to: "/my-route", label: "My Route" }],
};

const GUEST_ITEMS = [
  { to: "/", label: "Home" },
  { to: "/subscribe", label: "Subscribe" },
  { to: "/login", label: "Login" },
];

export default function AppNavbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const [logoutRequest] = useLogoutMutation();
  const [isOpen, setIsOpen] = useState(false);
  const { isAuthenticated, role } = useSelector((state) => state.auth);

  const navItems = isAuthenticated ? NAV_ITEMS_BY_ROLE[role] || [] : GUEST_ITEMS;
  const activeCompanyCategory =
    role === "COMPANY_ADMIN" ? getCompanyAdminActiveCategory(location.pathname) : null;

  const handleLogout = async () => {
    try {
      await logoutRequest().unwrap();
    } catch {
      // Standard catch for performance consistency
    }
    dispatch(logoutAction());
    navigate("/login", { replace: true });
    setIsOpen(false);
  };

  const navLinkClass = ({ isActive }, item) =>
    `relative text-[13px] font-bold px-4 py-2 transition-all duration-200 flex items-center gap-2 ${
      isActive || (role === "COMPANY_ADMIN" && activeCompanyCategory?.id === item.categoryId)
        ? "text-blue-600 after:content-[''] after:absolute after:bottom-[-13px] after:left-0 after:w-full after:h-[2px] after:bg-blue-600" 
        : "text-slate-500 hover:text-slate-900"
    }`;

  return (
    <header className="sticky top-0 z-50 w-full bg-white border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-6 h-[64px] flex items-center justify-between">
        
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="bg-blue-600 p-1.5 rounded-lg shadow-sm group-hover:bg-blue-700 transition-colors">
            <Truck className="text-white" size={18} />
          </div>
          <span className="text-base font-black tracking-tight text-slate-900 uppercase">
            Route<span className="text-blue-600">Master</span>
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center h-full gap-1">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={(state) => navLinkClass(state, item)}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Action Area */}
        <div className="hidden md:flex items-center gap-4 pl-4 border-l border-slate-100">
          {isAuthenticated ? (
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-end mr-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter leading-none">{role?.replace('_', ' ')}</span>
                <span className="text-xs font-bold text-slate-700 leading-tight">Active User</span>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-2 bg-slate-50 text-slate-600 text-xs font-bold px-4 py-2 rounded-xl border border-slate-200 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-100 transition-all"
              >
                <LogOut size={14} />
                Logout
              </button>
            </div>
          ) : (
            <Link 
              to="/login" 
              className="bg-blue-600 text-white text-xs font-bold px-6 py-2.5 rounded-xl hover:bg-blue-700 shadow-md shadow-blue-500/10 transition-all"
            >
              System Access
            </Link>
          )}
        </div>

        {/* Mobile Toggle */}
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className="md:hidden p-2 rounded-xl text-slate-600 hover:bg-slate-100 border border-transparent hover:border-slate-200 transition-all"
        >
          {isOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden absolute top-[64px] left-0 w-full bg-white border-b border-slate-200 shadow-xl px-4 py-6 animate-in slide-in-from-top-4 duration-200">
          <div className="flex flex-col gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => 
                  `text-sm font-bold px-4 py-3 rounded-xl transition-all ${
                    isActive || (role === "COMPANY_ADMIN" && activeCompanyCategory?.id === item.categoryId)
                      ? "bg-blue-50 text-blue-600"
                      : "text-slate-600"
                  }`
                }
                onClick={() => setIsOpen(false)}
              >
                {item.label}
              </NavLink>
            ))}
            {isAuthenticated && (
              <button
                type="button"
                onClick={handleLogout}
                className="mt-4 flex items-center justify-center gap-2 bg-rose-50 text-rose-600 text-sm font-bold py-3 rounded-xl border border-rose-100"
              >
                <LogOut size={16} />
                Sign Out
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
