import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { SnackbarProvider } from 'notistack';
import { QueryClient, QueryClientProvider } from 'react-query';

// Store
import useAuthStore from './store/authStore';

// Components
import ProtectedRoute from './components/ProtectedRoute';
import RoleBasedRedirect from './components/RoleBasedRedirect';
import Navigation from './components/Navigation';
import LoadingSpinner from './components/LoadingSpinner';

// Pages
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import StudentDashboard from './pages/student/StudentDashboard';
import StudentApplications from './pages/student/StudentApplications';
import StudentProfile from './pages/student/StudentProfile';
import InstituteDashboard from './pages/institute/InstituteDashboard';
import InstituteApplications from './pages/institute/InstituteApplications';
import InstituteReports from './pages/institute/InstituteReports';
import DepartmentDashboard from './pages/department/DepartmentDashboard';
import DepartmentApplications from './pages/department/DepartmentApplications';
import DepartmentReports from './pages/department/DepartmentReports';
import FinanceDashboard from './pages/finance/FinanceDashboard';
import FinanceApplications from './pages/finance/FinanceApplications';
import FinanceReports from './pages/finance/FinanceReports';
import AdminDashboard from './pages/admin/AdminDashboard';
import NotFoundPage from './pages/NotFoundPage';

// Create theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#dc004e',
      light: '#ff5983',
      dark: '#9a0036',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
        },
      },
    },
  },
});

// Create Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  const { initializeAuth, isAuthenticated, isLoading, user } = useAuthStore();

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <SnackbarProvider 
          maxSnack={3}
          anchorOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
        >
          <Router>
            <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
              {isAuthenticated && <Navigation />}
              
              <Box component="main" sx={{ flexGrow: 1 }}>
                <Routes>
                  {/* Public Routes */}
                  <Route 
                    path="/login" 
                    element={
                      isAuthenticated ? 
                        <RoleBasedRedirect user={user} /> : 
                        <LoginPage />
                    } 
                  />
                  <Route 
                    path="/register" 
                    element={
                      isAuthenticated ? 
                        <RoleBasedRedirect user={user} /> : 
                        <RegisterPage />
                    } 
                  />

                  {/* Protected Routes */}
                  <Route 
                    path="/" 
                    element={
                      isAuthenticated ? 
                        <RoleBasedRedirect user={user} /> : 
                        <Navigate to="/login" replace />
                    } 
                  />

                  {/* Student Routes */}
                  <Route
                    path="/student/dashboard"
                    element={
                      <ProtectedRoute allowedRoles={['student']}>
                        <StudentDashboard />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/student/applications"
                    element={
                      <ProtectedRoute allowedRoles={['student']}>
                        <StudentApplications />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/student/profile"
                    element={
                      <ProtectedRoute allowedRoles={['student']}>
                        <StudentProfile />
                      </ProtectedRoute>
                    }
                  />

                  {/* Institute Admin Routes */}
                  <Route
                    path="/institute/dashboard"
                    element={
                      <ProtectedRoute allowedRoles={['institute_admin']}>
                        <InstituteDashboard />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/institute/applications"
                    element={
                      <ProtectedRoute allowedRoles={['institute_admin']}>
                        <InstituteApplications />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/institute/reports"
                    element={
                      <ProtectedRoute allowedRoles={['institute_admin']}>
                        <InstituteReports />
                      </ProtectedRoute>
                    }
                  />

                  {/* Department Admin Routes */}
                  <Route
                    path="/department/dashboard"
                    element={
                      <ProtectedRoute allowedRoles={['department_admin']}>
                        <DepartmentDashboard />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/department/applications"
                    element={
                      <ProtectedRoute allowedRoles={['department_admin']}>
                        <DepartmentApplications />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/department/reports"
                    element={
                      <ProtectedRoute allowedRoles={['department_admin']}>
                        <DepartmentReports />
                      </ProtectedRoute>
                    }
                  />

                  {/* Finance Admin Routes */}
                  <Route
                    path="/finance/dashboard"
                    element={
                      <ProtectedRoute allowedRoles={['finance_admin']}>
                        <FinanceDashboard />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/finance/applications"
                    element={
                      <ProtectedRoute allowedRoles={['finance_admin']}>
                        <FinanceApplications />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/finance/reports"
                    element={
                      <ProtectedRoute allowedRoles={['finance_admin']}>
                        <FinanceReports />
                      </ProtectedRoute>
                    }
                  />

                  {/* Super Admin Routes */}
                  <Route
                    path="/admin/dashboard"
                    element={
                      <ProtectedRoute allowedRoles={['super_admin']}>
                        <AdminDashboard />
                      </ProtectedRoute>
                    }
                  />

                  {/* 404 Route */}
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Box>
            </Box>
          </Router>
        </SnackbarProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
