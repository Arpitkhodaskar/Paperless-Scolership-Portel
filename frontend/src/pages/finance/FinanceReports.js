import React from 'react';
import {
  Container,
  Typography,
  Alert,
} from '@mui/material';

const FinanceReports = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Finance Reports
      </Typography>
      
      <Alert severity="info">
        Finance reporting and analytics features will be implemented here.
      </Alert>
    </Container>
  );
};

export default FinanceReports;
