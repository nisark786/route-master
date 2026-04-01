export const COMPANY_ADMIN_NAV_CATEGORIES = [
  {
    id: "overview",
    label: "Overview",
    items: [{ to: "/company/dashboard", label: "Dashboard" }],
  },
  {
    id: "creation",
    label: "Creation",
    items: [
      { to: "/company/vehicles", label: "Vehicles" },
      { to: "/company/drivers", label: "Drivers" },
      { to: "/company/products", label: "Products" },
      { to: "/company/shops", label: "Shops" },
      { to: "/company/routes", label: "Routes" },
      { to: "/company/roles", label: "Roles" },
    ],
  },
  {
    id: "operations",
    label: "Operations",
    items: [
      { to: "/company/schedule", label: "Assignments" },
      { to: "/company/live-tracking", label: "Live Tracking" },
    ],
  },
  {
    id: "intelligence",
    label: "Intelligence",
    items: [
      { to: "/company/assistant", label: "AI Assistant" },
      { to: "/company/copilot", label: "Copilot" },
    ],
  },
  {
    id: "chat",
    label: "Chat",
    items: [
      { to: "/company/chat/drivers", label: "Drivers" },
      { to: "/company/chat/administration", label: "Administration" },
    ],
  },
  {
    id: "settings",
    label: "Settings",
    items: [
      { to: "/company/settings/profile", label: "Company Profile" },
      { to: "/company/settings/subscription", label: "Subscription" },
      { to: "/company/settings/billing", label: "Billing" },
      { to: "/company/settings/security", label: "Security" },
    ],
  },
];

export function getCompanyAdminActiveCategory(pathname) {
  return (
    COMPANY_ADMIN_NAV_CATEGORIES.find((category) =>
      category.items.some((item) => pathname === item.to || pathname.startsWith(`${item.to}/`))
    ) || COMPANY_ADMIN_NAV_CATEGORIES[0]
  );
}
