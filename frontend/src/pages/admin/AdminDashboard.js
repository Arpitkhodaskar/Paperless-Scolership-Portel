import React from 'react';
import {
  Container,
  Typography,
  Alert,
} from '@mui/material';

const AdminDashboard = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Admin Dashboard
      </Typography>
      
      <Alert severity="info">
        Super admin features for system management will be implemented here.
      </Alert>
    </Container>
  );
};

export default AdminDashboard;
