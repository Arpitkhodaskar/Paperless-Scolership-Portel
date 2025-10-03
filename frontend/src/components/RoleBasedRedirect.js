import React from 'react';
import { Navigate } from 'react-router-dom';

const RoleBasedRedirect = ({ user }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  switch (user.role) {
    case 'student':
      return <Navigate to="/student/dashboard" replace />;
    case 'institute_admin':
      return <Navigate to="/institute/dashboard" replace />;
    case 'department_admin':
      return <Navigate to="/department/dashboard" replace />;
    case 'finance_admin':
      return <Navigate to="/finance/dashboard" replace />;
    case 'super_admin':
      return <Navigate to="/admin/dashboard" replace />;
    default:
      return <Navigate to="/login" replace />;
  }
};

export default RoleBasedRedirect;
