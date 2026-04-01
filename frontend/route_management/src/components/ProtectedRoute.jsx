import { useSelector } from 'react-redux';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import SessionLoader from './SessionLoader';
import CompanyAdminShell from './CompanyAdminShell';

const ProtectedRoute = ({ allowedRoles }) => {
  const { role, isAuthenticated } = useSelector((state) => state.auth);
  const subscriptionGate = useSelector((state) => state.auth.subscriptionGate);
  const location = useLocation();


  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!role) {
    return <SessionLoader />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  if (
    role === "COMPANY_ADMIN" &&
    subscriptionGate &&
    location.pathname !== "/company/renew-subscription"
  ) {
    return <Navigate to="/company/renew-subscription" replace />;
  }

  if (role === "COMPANY_ADMIN" && location.pathname.startsWith("/company")) {
    return (
      <CompanyAdminShell>
        <Outlet />
      </CompanyAdminShell>
    );
  }

  return <Outlet />;
};

export default ProtectedRoute;
