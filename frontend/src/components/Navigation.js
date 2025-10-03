import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard,
  Assignment,
  Assessment,
  AccountCircle,
  Logout,
  School,
  Business,
  AccountBalance,
  AdminPanelSettings,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import useAuthStore from '../store/authStore';

const Navigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const { user, logout } = useAuthStore();
  const [anchorEl, setAnchorEl] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleProfileMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getNavigationItems = () => {
    const role = user?.role;
    const baseItems = [];

    switch (role) {
      case 'student':
        baseItems.push(
          { text: 'Dashboard', icon: <Dashboard />, path: '/student/dashboard' },
          { text: 'Applications', icon: <Assignment />, path: '/student/applications' },
          { text: 'Profile', icon: <AccountCircle />, path: '/student/profile' }
        );
        break;
      case 'institute_admin':
        baseItems.push(
          { text: 'Dashboard', icon: <Dashboard />, path: '/institute/dashboard' },
          { text: 'Applications', icon: <Assignment />, path: '/institute/applications' },
          { text: 'Reports', icon: <Assessment />, path: '/institute/reports' }
        );
        break;
      case 'department_admin':
        baseItems.push(
          { text: 'Dashboard', icon: <Dashboard />, path: '/department/dashboard' },
          { text: 'Applications', icon: <Assignment />, path: '/department/applications' },
          { text: 'Reports', icon: <Assessment />, path: '/department/reports' }
        );
        break;
      case 'finance_admin':
        baseItems.push(
          { text: 'Dashboard', icon: <Dashboard />, path: '/finance/dashboard' },
          { text: 'Applications', icon: <Assignment />, path: '/finance/applications' },
          { text: 'Reports', icon: <Assessment />, path: '/finance/reports' }
        );
        break;
      case 'super_admin':
        baseItems.push(
          { text: 'Dashboard', icon: <Dashboard />, path: '/admin/dashboard' }
        );
        break;
      default:
        break;
    }

    return baseItems;
  };

  const getRoleIcon = () => {
    switch (user?.role) {
      case 'student':
        return <School />;
      case 'institute_admin':
        return <Business />;
      case 'department_admin':
        return <Business />;
      case 'finance_admin':
        return <AccountBalance />;
      case 'super_admin':
        return <AdminPanelSettings />;
      default:
        return <AccountCircle />;
    }
  };

  const getRoleTitle = () => {
    switch (user?.role) {
      case 'student':
        return 'Student Portal';
      case 'institute_admin':
        return 'Institute Admin';
      case 'department_admin':
        return 'Department Admin';
      case 'finance_admin':
        return 'Finance Admin';
      case 'super_admin':
        return 'Super Admin';
      default:
        return 'Portal';
    }
  };

  const navigationItems = getNavigationItems();

  const drawer = (
    <Box>
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 1 }}>
          {getRoleIcon()}
          <Typography variant="h6" sx={{ ml: 1 }}>
            {getRoleTitle()}
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          {user?.email}
        </Typography>
      </Box>
      <Divider />
      <List>
        {navigationItems.map((item) => (
          <ListItem
            button
            key={item.text}
            onClick={() => {
              navigate(item.path);
              if (isMobile) setMobileOpen(false);
            }}
            selected={location.pathname === item.path}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItem>
        ))}
      </List>
      <Divider />
      <List>
        <ListItem button onClick={handleLogout}>
          <ListItemIcon>
            <Logout />
          </ListItemIcon>
          <ListItemText primary="Logout" />
        </ListItem>
      </List>
    </Box>
  );

  return (
    <>
      <AppBar position="sticky">
        <Toolbar>
          {isMobile && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}
          
          <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
            {getRoleIcon()}
            <Typography variant="h6" component="div" sx={{ ml: 1 }}>
              Scholarship Portal
            </Typography>
          </Box>

          {!isMobile && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              {navigationItems.map((item) => (
                <Button
                  key={item.text}
                  color="inherit"
                  onClick={() => navigate(item.path)}
                  sx={{
                    backgroundColor: location.pathname === item.path ? 'rgba(255,255,255,0.1)' : 'transparent',
                  }}
                >
                  {item.text}
                </Button>
              ))}
            </Box>
          )}

          <IconButton
            size="large"
            edge="end"
            aria-label="account of current user"
            aria-controls="primary-search-account-menu"
            aria-haspopup="true"
            onClick={handleProfileMenuOpen}
            color="inherit"
            sx={{ ml: 1 }}
          >
            <Avatar sx={{ width: 32, height: 32 }}>
              {user?.email?.charAt(0).toUpperCase()}
            </Avatar>
          </IconButton>
        </Toolbar>
      </AppBar>

      <Menu
        id="primary-search-account-menu"
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        keepMounted
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>
          <AccountCircle sx={{ mr: 1 }} /> Profile
        </MenuItem>
        <MenuItem onClick={handleLogout}>
          <Logout sx={{ mr: 1 }} /> Logout
        </MenuItem>
      </Menu>

      {isMobile && (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 280 },
          }}
        >
          {drawer}
        </Drawer>
      )}
    </>
  );
};

export default Navigation;
