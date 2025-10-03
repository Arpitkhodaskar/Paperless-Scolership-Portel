import React from 'react';
import {
  Container,
  Typography,
  Alert,
} from '@mui/material';

const DepartmentReports = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Department Reports
      </Typography>
      
      <Alert severity="info">
        Department reporting features will be implemented here.
      </Alert>
    </Container>
  );
};

export default DepartmentReports;
