import { lazy } from "react";

const AdminChatPage = lazy(() => import("../pages/mainAdmin/AdminChatPage"));
const AdminCompaniesPage = lazy(() => import("../pages/mainAdmin/AdminCompaniesPage"));
const MainAdminDashboard = lazy(() => import("../pages/mainAdmin/MainAdminDashboard"));
const AdminSubscriptionsPage = lazy(() => import("../pages/mainAdmin/AdminSubscriptionsPage"));
const CompanyAdminDashboardPage = lazy(() => import("../pages/companyAdmin/CompanyAdminDashboardPage"));
const CompanyVehiclesPage = lazy(() => import("../pages/companyAdmin/CompanyVehiclesPage"));
const CompanyProductsPage = lazy(() => import("../pages/companyAdmin/CompanyProductsPage"));
const CompanyDriversPage = lazy(() => import("../pages/companyAdmin/CompanyDriversPage"));
const CompanyShopsPage = lazy(() => import("../pages/companyAdmin/CompanyShopsPage"));
const CompanyRoutesPage = lazy(() => import("../pages/companyAdmin/CompanyRoutesPage"));
const CompanyRouteDetailPage = lazy(() => import("../pages/companyAdmin/CompanyRouteDetailPage"));
const CompanySchedulePage = lazy(() => import("../pages/companyAdmin/CompanySchedulePage"));
const CompanyRolesPage = lazy(() => import("../pages/companyAdmin/CompanyRolesPage"));
const CompanyAiAssistantPage = lazy(() => import("../pages/companyAdmin/CompanyAiAssistantPage"));
const CompanyCopilotPage = lazy(() => import("../pages/companyAdmin/CompanyCopilotPage"));
const CompanyLiveTrackingPage = lazy(() => import("../pages/companyAdmin/CompanyLiveTrackingPage"));
const CompanyDriverChatPage = lazy(() => import("../pages/companyAdmin/CompanyDriverChatPage"));
const CompanyAdministrationChatPage = lazy(() => import("../pages/companyAdmin/CompanyAdministrationChatPage"));
const CompanySubscriptionRenewPage = lazy(() => import("../pages/companyAdmin/CompanySubscriptionRenewPage"));
const CompanySettingsProfilePage = lazy(() => import("../pages/companyAdmin/CompanySettingsProfilePage"));
const CompanySettingsSubscriptionPage = lazy(() => import("../pages/companyAdmin/CompanySettingsSubscriptionPage"));
const CompanySettingsBillingPage = lazy(() => import("../pages/companyAdmin/CompanySettingsBillingPage"));
const CompanySettingsSecurityPage = lazy(() => import("../pages/companyAdmin/CompanySettingsSecurityPage"));

export const DEFAULT_AUTH_ROUTE = "/company/dashboard";

export const PROTECTED_ROUTE_GROUPS = [
  {
    roles: ["SUPER_ADMIN"],
    routes: [
      { path: "/admin/dashboard", element: <MainAdminDashboard /> },
      { path: "/admin/companies", element: <AdminCompaniesPage /> },
      { path: "/admin/subscriptions", element: <AdminSubscriptionsPage /> },
      { path: "/admin/chat", element: <AdminChatPage /> },
    ],
  },
  {
    roles: ["COMPANY_ADMIN"],
    routes: [
      { path: "/company/dashboard", element: <CompanyAdminDashboardPage /> },
      { path: "/company/vehicles", element: <CompanyVehiclesPage /> },
      { path: "/company/products", element: <CompanyProductsPage /> },
      { path: "/company/drivers", element: <CompanyDriversPage /> },
      { path: "/company/schedule", element: <CompanySchedulePage /> },
      { path: "/company/shops", element: <CompanyShopsPage /> },
      { path: "/company/routes", element: <CompanyRoutesPage /> },
      { path: "/company/routes/:routeId", element: <CompanyRouteDetailPage /> },
      { path: "/company/roles", element: <CompanyRolesPage /> },
      { path: "/company/assistant", element: <CompanyAiAssistantPage /> },
      { path: "/company/copilot", element: <CompanyCopilotPage /> },
      { path: "/company/live-tracking", element: <CompanyLiveTrackingPage /> },
      { path: "/company/chat/drivers", element: <CompanyDriverChatPage /> },
      { path: "/company/chat/administration", element: <CompanyAdministrationChatPage /> },
      { path: "/company/renew-subscription", element: <CompanySubscriptionRenewPage /> },
      { path: "/company/settings/profile", element: <CompanySettingsProfilePage /> },
      { path: "/company/settings/subscription", element: <CompanySettingsSubscriptionPage /> },
      { path: "/company/settings/billing", element: <CompanySettingsBillingPage /> },
      { path: "/company/settings/security", element: <CompanySettingsSecurityPage /> },
    ],
  },
  {
    roles: ["SUPER_ADMIN", "DRIVER"],
    routes: [{ path: "/my-route", element: <div>Active Route Tracking</div> }],
  },
];
