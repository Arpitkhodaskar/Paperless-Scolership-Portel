import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  LinearProgress,
  Divider,
} from '@mui/material';
import {
  AccountBalance,
  Payment,
  Assessment,
  TrendingUp,
  CheckCircle,
  Schedule,
  MonetizationOn,
  Receipt,
  Calculate,
  Send,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useSnackbar } from 'notistack';
import { financeAPI } from '../../services/api';

const FinanceDashboard = () => {
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  
  const [selectedApplication, setSelectedApplication] = useState(null);
  const [openCalculateDialog, setOpenCalculateDialog] = useState(false);
  const [openPaymentDialog, setOpenPaymentDialog] = useState(false);
  const [openDBTDialog, setOpenDBTDialog] = useState(false);
  
  const [calculationData, setCalculationData] = useState({
    tuition_fee_amount: '',
    maintenance_allowance: '',
    other_allowances: '',
  });
  
  const [paymentData, setPaymentData] = useState({
    payment_type: '',
    amount: '',
    remarks: '',
  });

  // Fetch finance dashboard data
  const { data: dashboardData, isLoading } = useQuery(
    'financeDashboard',
    () => financeAPI.getDashboard()
  );

  // Fetch pending applications
  const { data: applications } = useQuery(
    'financeApplications',
    () => financeAPI.getPendingApplications()
  );

  // Calculate scholarship mutation
  const calculateMutation = useMutation(
    ({ applicationId, data }) => financeAPI.calculateScholarship(applicationId, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['financeDashboard', 'financeApplications']);
        enqueueSnackbar('Scholarship amount calculated successfully!', { variant: 'success' });
        setOpenCalculateDialog(false);
        setSelectedApplication(null);
      },
      onError: (error) => {
        enqueueSnackbar(error.response?.data?.message || 'Failed to calculate scholarship', { 
          variant: 'error' 
        });
      },
    }
  );

  // Update payment status mutation
  const paymentMutation = useMutation(
    ({ applicationId, data }) => financeAPI.updatePaymentStatus(applicationId, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['financeDashboard', 'financeApplications']);
        enqueueSnackbar('Payment status updated successfully!', { variant: 'success' });
        setOpenPaymentDialog(false);
        setSelectedApplication(null);
      },
      onError: (error) => {
        enqueueSnackbar(error.response?.data?.message || 'Failed to update payment status', { 
          variant: 'error' 
        });
      },
    }
  );

  // DBT transfer mutation
  const dbtMutation = useMutation(
    (applicationId) => financeAPI.simulateDBTTransfer(applicationId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['financeDashboard', 'financeApplications']);
        enqueueSnackbar('DBT transfer initiated successfully!', { variant: 'success' });
        setOpenDBTDialog(false);
        setSelectedApplication(null);
      },
      onError: (error) => {
        enqueueSnackbar(error.response?.data?.message || 'Failed to initiate DBT transfer', { 
          variant: 'error' 
        });
      },
    }
  );

  const handleCalculateScholarship = (application) => {
    setSelectedApplication(application);
    setCalculationData({
      tuition_fee_amount: '',
      maintenance_allowance: '',
      other_allowances: '',
    });
    setOpenCalculateDialog(true);
  };

  const handleUpdatePayment = (application) => {
    setSelectedApplication(application);
    setPaymentData({
      payment_type: '',
      amount: '',
      remarks: '',
    });
    setOpenPaymentDialog(true);
  };

  const handleDBTTransfer = (application) => {
    setSelectedApplication(application);
    setOpenDBTDialog(true);
  };

  const submitCalculation = () => {
    calculateMutation.mutate({
      applicationId: selectedApplication.id,
      data: calculationData,
    });
  };

  const submitPayment = () => {
    paymentMutation.mutate({
      applicationId: selectedApplication.id,
      data: paymentData,
    });
  };

  const submitDBTTransfer = () => {
    dbtMutation.mutate(selectedApplication.id);
  };

  if (isLoading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <LinearProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading finance dashboard...
        </Typography>
      </Container>
    );
  }

  const stats = dashboardData || {};

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Finance Dashboard
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Manage scholarship calculations, payments, and DBT transfers
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    Total Applications
                  </Typography>
                  <Typography variant="h4">
                    {stats.total_applications || 0}
                  </Typography>
                </Box>
                <Assessment color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    Pending Calculations
                  </Typography>
                  <Typography variant="h4" color="warning.main">
                    {stats.pending_calculations || 0}
                  </Typography>
                </Box>
                <Calculate color="warning" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    Total Disbursed
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    ₹{(stats.total_disbursed || 0).toLocaleString()}
                  </Typography>
                </Box>
                <MonetizationOn color="success" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    Pending Payments
                  </Typography>
                  <Typography variant="h4" color="error.main">
                    {stats.pending_payments || 0}
                  </Typography>
                </Box>
                <Payment color="error" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Applications Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Applications Requiring Finance Action
          </Typography>
          
          {applications && applications.length > 0 ? (
            <TableContainer component={Paper} sx={{ mt: 2 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Application ID</TableCell>
                    <TableCell>Student Name</TableCell>
                    <TableCell>Scholarship Type</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {applications.map((application) => (
                    <TableRow key={application.id}>
                      <TableCell>{application.id}</TableCell>
                      <TableCell>
                        {application.student_name || `${application.student?.first_name} ${application.student?.last_name}`}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={application.scholarship_type?.replace('_', ' ').toUpperCase()}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={application.status?.replace('_', ' ').toUpperCase()}
                          color={application.status === 'approved' ? 'success' : 'warning'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {application.calculated_amount ? 
                          `₹${Number(application.calculated_amount).toLocaleString()}` : 
                          'Not calculated'
                        }
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          {!application.calculated_amount && (
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<Calculate />}
                              onClick={() => handleCalculateScholarship(application)}
                            >
                              Calculate
                            </Button>
                          )}
                          
                          {application.calculated_amount && application.payment_status !== 'completed' && (
                            <Button
                              size="small"
                              variant="outlined"
                              color="success"
                              startIcon={<Payment />}
                              onClick={() => handleUpdatePayment(application)}
                            >
                              Update Payment
                            </Button>
                          )}
                          
                          {application.payment_status === 'completed' && !application.dbt_transfer_status && (
                            <Button
                              size="small"
                              variant="outlined"
                              color="secondary"
                              startIcon={<Send />}
                              onClick={() => handleDBTTransfer(application)}
                            >
                              DBT Transfer
                            </Button>
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Alert severity="info" sx={{ mt: 2 }}>
              No applications requiring finance action at the moment.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Calculate Scholarship Dialog */}
      <Dialog open={openCalculateDialog} onClose={() => setOpenCalculateDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Calculate Scholarship Amount</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Application ID: {selectedApplication?.id}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Student: {selectedApplication?.student_name}
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Tuition Fee Amount"
                type="number"
                value={calculationData.tuition_fee_amount}
                onChange={(e) => setCalculationData(prev => ({...prev, tuition_fee_amount: e.target.value}))}
                InputProps={{ startAdornment: '₹' }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Maintenance Allowance"
                type="number"
                value={calculationData.maintenance_allowance}
                onChange={(e) => setCalculationData(prev => ({...prev, maintenance_allowance: e.target.value}))}
                InputProps={{ startAdornment: '₹' }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Other Allowances"
                type="number"
                value={calculationData.other_allowances}
                onChange={(e) => setCalculationData(prev => ({...prev, other_allowances: e.target.value}))}
                InputProps={{ startAdornment: '₹' }}
              />
            </Grid>
          </Grid>
          
          <Alert severity="info" sx={{ mt: 2 }}>
            Total Amount: ₹{(
              Number(calculationData.tuition_fee_amount || 0) + 
              Number(calculationData.maintenance_allowance || 0) + 
              Number(calculationData.other_allowances || 0)
            ).toLocaleString()}
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCalculateDialog(false)}>Cancel</Button>
          <Button 
            onClick={submitCalculation} 
            variant="contained"
            disabled={calculateMutation.isLoading}
          >
            Calculate & Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Update Payment Dialog */}
      <Dialog open={openPaymentDialog} onClose={() => setOpenPaymentDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Update Payment Status</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Application ID: {selectedApplication?.id}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Calculated Amount: ₹{Number(selectedApplication?.calculated_amount || 0).toLocaleString()}
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Payment Type</InputLabel>
                <Select
                  value={paymentData.payment_type}
                  label="Payment Type"
                  onChange={(e) => setPaymentData(prev => ({...prev, payment_type: e.target.value}))}
                >
                  <MenuItem value="tuition_fee">Tuition Fee</MenuItem>
                  <MenuItem value="maintenance_allowance">Maintenance Allowance</MenuItem>
                  <MenuItem value="full_payment">Full Payment</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Amount"
                type="number"
                value={paymentData.amount}
                onChange={(e) => setPaymentData(prev => ({...prev, amount: e.target.value}))}
                InputProps={{ startAdornment: '₹' }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Remarks"
                multiline
                rows={2}
                value={paymentData.remarks}
                onChange={(e) => setPaymentData(prev => ({...prev, remarks: e.target.value}))}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenPaymentDialog(false)}>Cancel</Button>
          <Button 
            onClick={submitPayment} 
            variant="contained"
            disabled={paymentMutation.isLoading}
          >
            Update Payment
          </Button>
        </DialogActions>
      </Dialog>

      {/* DBT Transfer Dialog */}
      <Dialog open={openDBTDialog} onClose={() => setOpenDBTDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Initiate DBT Transfer</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Application ID: {selectedApplication?.id}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Student: {selectedApplication?.student_name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Amount: ₹{Number(selectedApplication?.calculated_amount || 0).toLocaleString()}
          </Typography>
          
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will initiate a Direct Benefit Transfer (DBT) to the student's bank account. 
            Please ensure all details are verified before proceeding.
          </Alert>
          
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>Transfer Details:</Typography>
            <Typography variant="body2">Bank Account: {selectedApplication?.student?.bank_account_number || 'Not provided'}</Typography>
            <Typography variant="body2">IFSC Code: {selectedApplication?.student?.bank_ifsc_code || 'Not provided'}</Typography>
            <Typography variant="body2">Bank Name: {selectedApplication?.student?.bank_name || 'Not provided'}</Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDBTDialog(false)}>Cancel</Button>
          <Button 
            onClick={submitDBTTransfer} 
            variant="contained"
            color="secondary"
            disabled={dbtMutation.isLoading}
          >
            Initiate Transfer
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default FinanceDashboard;
