import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAtom } from 'jotai';
import { authAtom } from '../../store/auth';

interface ProtectedRouteProps {
  children: React.ReactElement;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated } = authAtom();
  const [isAuthenticatedValue] = useAtom(isAuthenticated);
  const location = useLocation();

  if (!isAuthenticatedValue) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export default ProtectedRoute;