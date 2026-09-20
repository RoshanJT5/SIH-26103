import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useCurrentUser } from "../utils/auth";

export default function ProtectedRoute() {
  const { user } = useCurrentUser();
  const location = useLocation();

  if (!user) {
    const destination = location.pathname + location.search;
    const redirectParam = encodeURIComponent(destination);
    return (
      <Navigate
        to={`/login?redirect=${redirectParam}&reason=auth_required`}
        replace
      />
    );
  }

  return <Outlet />;
}
