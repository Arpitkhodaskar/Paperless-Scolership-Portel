import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authAPI, getUserData, getUserRole, isAuthenticated } from '../services/api';

const useAuthStore = create(
  persist(
    (set, get) => ({
      // State
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authAPI.login({ email, password });
          
          // Store token and user data
          localStorage.setItem('token', response.access_token);
          localStorage.setItem('user', JSON.stringify(response.user));
          
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
          return { success: true, user: response.user };
        } catch (error) {
          const errorMessage = error.response?.data?.message || 'Login failed';
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: errorMessage,
          });
          return { success: false, error: errorMessage };
        }
      },

      register: async (userData) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authAPI.register(userData);
          set({ isLoading: false, error: null });
          return response;
        } catch (error) {
          set({
            isLoading: false,
            error: error.message || 'Registration failed',
          });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          await authAPI.logout();
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          // Clear local storage
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });
        }
      },

      refreshUser: async () => {
        if (!isAuthenticated()) {
          set({
            user: null,
            isAuthenticated: false,
          });
          return;
        }

        try {
          const userData = await authAPI.getCurrentUser();
          set({
            user: userData,
            isAuthenticated: true,
          });
        } catch (error) {
          console.error('Failed to refresh user:', error);
          set({
            user: null,
            isAuthenticated: false,
          });
        }
      },

      clearError: () => set({ error: null }),

      // Initialize auth state from localStorage
      initializeAuth: () => {
        set({ isLoading: true });
        
        try {
          const token = localStorage.getItem('token');
          const userData = localStorage.getItem('user');
          
          if (token && userData) {
            const user = JSON.parse(userData);
            
            // Check if token is expired (add some buffer time)
            try {
              const decodedToken = jwtDecode(token);
              if (decodedToken.exp * 1000 > Date.now() + 60000) { // 1 minute buffer
                set({
                  isAuthenticated: true,
                  user,
                  token,
                  isLoading: false,
                });
                return;
              } else {
                // Token expired, clean up
                localStorage.removeItem('token');
                localStorage.removeItem('user');
              }
            } catch (jwtError) {
              // Invalid token, clean up
              localStorage.removeItem('token');
              localStorage.removeItem('user');
            }
          }
          
          set({
            isAuthenticated: false,
            user: null,
            token: null,
            isLoading: false,
          });
        } catch (error) {
          console.error('Error initializing auth:', error);
          set({
            isAuthenticated: false,
            user: null,
            token: null,
            isLoading: false,
          });
        }
      },

      // Role-based helpers
      isStudent: () => {
        const { user } = get();
        return user?.role === 'student';
      },

      isInstituteAdmin: () => {
        const { user } = get();
        return user?.role === 'institute_admin';
      },

      isDepartmentAdmin: () => {
        const { user } = get();
        return user?.role === 'department_admin';
      },

      isFinanceAdmin: () => {
        const { user } = get();
        return user?.role === 'finance_admin';
      },

      isSuperAdmin: () => {
        const { user } = get();
        return user?.role === 'super_admin';
      },

      hasRole: (role) => {
        const { user } = get();
        return user?.role === role;
      },

      hasAnyRole: (roles) => {
        const { user } = get();
        return roles.includes(user?.role);
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;
