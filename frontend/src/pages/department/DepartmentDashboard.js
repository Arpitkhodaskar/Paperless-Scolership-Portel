import React from 'react';
import {
  Container,
  Typography,
  Box,
  Alert,
} from '@mui/material';

const DepartmentDashboard = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Department Dashboard
      </Typography>
      
      <Alert severity="info">
        Department management features will be implemented here.
      </Alert>
    </Container>
  );
};

export default DepartmentDashboard;
