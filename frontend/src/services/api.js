import axios from 'axios';
import jwtDecode from 'jwt-decode';

// Base API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });
          
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          originalRequest.headers.Authorization = `Bearer ${access}`;
          
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_data');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Authentication API
export const authAPI = {
  // Login
  login: async (credentials) => {
    try {
      const response = await api.post('/auth/login/', credentials);
      const { access, refresh, user } = response.data;
      
      // Store tokens and user data
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('user_data', JSON.stringify(user));
      
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  // Register
  register: async (userData) => {
    try {
      const response = await api.post('/auth/register/', userData);
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  // Logout
  logout: async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await api.post('/auth/logout/', { refresh: refreshToken });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage regardless of API response
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_data');
    }
  },

  // Get current user
  getCurrentUser: async () => {
    try {
      const response = await api.get('/auth/profile/');
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  // Refresh token
  refreshToken: async (refreshToken) => {
    try {
      const response = await api.post('/auth/refresh/', {
        refresh: refreshToken,
      });
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  // Change password
  changePassword: async (passwordData) => {
    try {
      const response = await api.post('/auth/change-password/', passwordData);
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },
};

// Students API
export const studentsAPI = {
  // Get student profile
  getProfile: async () => {
    const response = await api.get('/students/profile/');
    return response.data;
  },

  // Update student profile
  updateProfile: async (profileData) => {
    const response = await api.put('/students/profile/', profileData);
    return response.data;
  },

  // Get applications
  getApplications: async (params = {}) => {
    const response = await api.get('/students/applications/', { params });
    return response.data;
  },

  // Submit application
  submitApplication: async (applicationData) => {
    const response = await api.post('/students/applications/', applicationData);
    return response.data;
  },

  // Get application details
  getApplicationDetail: async (applicationId) => {
    const response = await api.get(`/students/applications/${applicationId}/`);
    return response.data;
  },

  // Update application
  updateApplication: async (applicationId, applicationData) => {
    const response = await api.put(`/students/applications/${applicationId}/`, applicationData);
    return response.data;
  },

  // Upload documents
  uploadDocument: async (applicationId, documentData) => {
    const formData = new FormData();
    Object.keys(documentData).forEach(key => {
      formData.append(key, documentData[key]);
    });
    
    const response = await api.post(
      `/students/applications/${applicationId}/documents/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // Get dashboard data
  getDashboard: async () => {
    const response = await api.get('/students/dashboard/');
    return response.data;
  },

  // Get statistics
  getStatistics: async () => {
    const response = await api.get('/students/statistics/');
    return response.data;
  },
};

// Institutes API
export const institutesAPI = {
  // Get pending applications
  getPendingApplications: async (params = {}) => {
    const response = await api.get('/institutes/applications/pending/', { params });
    return response.data;
  },

  // Review application
  reviewApplication: async (applicationId, reviewData) => {
    const response = await api.post(`/institutes/applications/${applicationId}/review/`, reviewData);
    return response.data;
  },

  // Get dashboard data
  getDashboard: async () => {
    const response = await api.get('/institutes/dashboard/');
    return response.data;
  },

  // Get reports
  getReports: async (reportType, params = {}) => {
    const response = await api.get(`/institutes/reports/${reportType}/`, { params });
    return response.data;
  },

  // Get statistics
  getStatistics: async () => {
    const response = await api.get('/institutes/statistics/');
    return response.data;
  },

  // Bulk operations
  bulkAction: async (actionData) => {
    const response = await api.post('/institutes/applications/bulk/action/', actionData);
    return response.data;
  },
};

// Departments API
export const departmentsAPI = {
  // Get verified applications
  getVerifiedApplications: async (params = {}) => {
    const response = await api.get('/departments/applications/verified/', { params });
    return response.data;
  },

  // Review application
  reviewApplication: async (applicationId, reviewData) => {
    const response = await api.post(`/departments/applications/${applicationId}/review/`, reviewData);
    return response.data;
  },

  // Forward to finance
  forwardToFinance: async (forwardData) => {
    const response = await api.post('/departments/finance/forward/', forwardData);
    return response.data;
  },

  // Get dashboard data
  getDashboard: async () => {
    const response = await api.get('/departments/dashboard/');
    return response.data;
  },

  // Get reports
  getReports: async (reportType, params = {}) => {
    const response = await api.get(`/departments/reports/${reportType}/`, { params });
    return response.data;
  },

  // Get statistics
  getStatistics: async () => {
    const response = await api.get('/departments/statistics/');
    return response.data;
  },
};

// Finance API
export const financeAPI = {
  // Get pending applications
  getPendingApplications: async (params = {}) => {
    const response = await api.get('/finance/applications/pending/', { params });
    return response.data;
  },

  // Calculate scholarship amount
  calculateAmount: async (calculationData) => {
    const response = await api.post('/finance/calculate/', calculationData);
    return response.data;
  },

  // Update payment status
  updatePaymentStatus: async (paymentData) => {
    const response = await api.post('/finance/payments/status/', paymentData);
    return response.data;
  },

  // DBT transfer
  dbtTransfer: async (transferData) => {
    const response = await api.post('/finance/dbt/transfer/', transferData);
    return response.data;
  },

  // Bulk disbursements
  bulkDisbursements: async (disbursementData) => {
    const response = await api.post('/finance/disbursements/bulk/', disbursementData);
    return response.data;
  },

  // Get dashboard data
  getDashboard: async () => {
    const response = await api.get('/finance/dashboard/');
    return response.data;
  },

  // Get reports
  getReports: async (reportType, params = {}) => {
    const response = await api.get(`/finance/reports/${reportType}/`, { params });
    return response.data;
  },

  // Get statistics
  getStatistics: async () => {
    const response = await api.get('/finance/statistics/');
    return response.data;
  },
};

// Utility functions
export const getAuthToken = () => {
  return localStorage.getItem('access_token');
};

export const isAuthenticated = () => {
  const token = getAuthToken();
  if (!token) return false;

  try {
    const decoded = jwtDecode(token);
    return decoded.exp > Date.now() / 1000;
  } catch (error) {
    return false;
  }
};

export const getUserData = () => {
  const userData = localStorage.getItem('user_data');
  return userData ? JSON.parse(userData) : null;
};

export const getUserRole = () => {
  const userData = getUserData();
  return userData?.role || null;
};

export default api;
