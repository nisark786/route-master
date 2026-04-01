import { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useSelector } from "react-redux";
import ProtectedRoute from "./components/ProtectedRoute";
import SessionLoader from "./components/SessionLoader";
import Login from "./pages/Login";
import Home from "./pages/Home";
import Payment from "./pages/Payment";
import useAuthBootstrap from "./features/auth/useAuthBootstrap";
import useAdminPrefetch from "./features/admin/useAdminPrefetch";
import { DEFAULT_AUTH_ROUTE, PROTECTED_ROUTE_GROUPS } from "./routes/routeConfig.jsx";
import AppNavbar from "./components/AppNavbar";

export default function App() {
  useAuthBootstrap();
  useAdminPrefetch();
  const { isInitialized, isAuthenticated, role } = useSelector((state) => state.auth);
  const landingRouteByRole = {
    SUPER_ADMIN: "/admin/dashboard",
    COMPANY_ADMIN: DEFAULT_AUTH_ROUTE,
    DRIVER: "/my-route",
  };
  const landingRoute = landingRouteByRole[role] || DEFAULT_AUTH_ROUTE;

  if (!isInitialized) {
    return <SessionLoader />;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <AppNavbar />
      <Routes>
        <Route path="/" element={<Home />} />

        {/* Auth Gate: Logged in users get sent home, logged out users stay on Login */}
        <Route
          path="/login"
          element={!isAuthenticated ? <Login /> : role ? <Navigate to={landingRoute} replace /> : <SessionLoader />}
        />

        <Route
          path="/subscribe"
          element={!isAuthenticated ? <Payment /> : role ? <Navigate to={landingRoute} replace /> : <SessionLoader />}
        />

        {PROTECTED_ROUTE_GROUPS.map((group) => (
          <Route
            key={group.roles.join("-")}
            element={<ProtectedRoute allowedRoles={group.roles} />}
          >
            {group.routes.map((route) => (
              <Route
                key={route.path}
                path={route.path}
                element={<Suspense fallback={<SessionLoader />}>{route.element}</Suspense>}
              />
            ))}
          </Route>
        ))}

        <Route path="/unauthorized" element={<div className="p-10 text-center">Access Denied</div>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
