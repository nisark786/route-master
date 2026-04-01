import { NavLink, useLocation } from "react-router-dom";
import { PanelLeft } from "lucide-react";
import { useSelector } from "react-redux";

import {
  getCompanyAdminActiveCategory,
} from "../routes/companyAdminNavigation";

export default function CompanyAdminShell({ children }) {
  const location = useLocation();
  const subscriptionGate = useSelector((state) => state.auth.subscriptionGate);
  const activeCategory = getCompanyAdminActiveCategory(location.pathname);

  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      <div className="mx-auto flex w-full max-w-[1600px]">
        <aside className="hidden w-72 shrink-0 lg:block">
          <div className="fixed top-[64px] bottom-0 w-72 border-r border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-6 py-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-600 text-white">
                  <PanelLeft size={18} />
                </div>
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                    Company Admin
                  </p>
                  <h2 className="text-lg font-black text-slate-900">{activeCategory.label}</h2>
                </div>
              </div>
            </div>

            <div className="space-y-2 px-4 py-5">
              {activeCategory.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `block rounded-md border px-4 py-3 text-sm font-bold transition-all ${
                      isActive
                        ? "border-blue-600 bg-blue-600 text-white"
                        : "border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          {subscriptionGate ? (
            <div className="mx-4 mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
              {subscriptionGate.message || "Subscription access is restricted until renewal is completed."}
            </div>
          ) : null}
          {children}
        </main>
      </div>
    </div>
  );
}
