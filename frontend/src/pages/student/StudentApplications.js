import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Chip,
  IconButton,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
} from '@mui/material';
import {
  Add,
  Visibility,
  Edit,
  Delete,
  CloudUpload,
  Download,
  CheckCircle,
  Schedule,
  Cancel,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useSnackbar } from 'notistack';
import { studentsAPI } from '../../services/api';

const StudentApplications = () => {
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  
  const [openDialog, setOpenDialog] = useState(false);
  const [editingApplication, setEditingApplication] = useState(null);
  const [formData, setFormData] = useState({
    scholarship_type: '',
    course_name: '',
    institution_name: '',
    academic_year: '',
    family_income: '',
    category: '',
    marks_percentage: '',
    documents: null,
  });

  // Fetch applications
  const { data: applications, isLoading } = useQuery(
    'studentApplications',
    () => studentsAPI.getMyApplications()
  );

  // Create application mutation
  const createMutation = useMutation(
    (data) => studentsAPI.createApplication(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('studentApplications');
        enqueueSnackbar('Application submitted successfully!', { variant: 'success' });
        handleCloseDialog();
      },
      onError: (error) => {
        enqueueSnackbar(error.response?.data?.message || 'Failed to submit application', { 
          variant: 'error' 
        });
      },
    }
  );

  // Update application mutation
  const updateMutation = useMutation(
    ({ id, data }) => studentsAPI.updateApplication(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('studentApplications');
        enqueueSnackbar('Application updated successfully!', { variant: 'success' });
        handleCloseDialog();
      },
      onError: (error) => {
        enqueueSnackbar(error.response?.data?.message || 'Failed to update application', { 
          variant: 'error' 
        });
      },
    }
  );

  const handleOpenDialog = (application = null) => {
    if (application) {
      setEditingApplication(application);
      setFormData({
        scholarship_type: application.scholarship_type || '',
        course_name: application.course_name || '',
        institution_name: application.institution_name || '',
        academic_year: application.academic_year || '',
        family_income: application.family_income || '',
        category: application.category || '',
        marks_percentage: application.marks_percentage || '',
        documents: null,
      });
    } else {
      setEditingApplication(null);
      setFormData({
        scholarship_type: '',
        course_name: '',
        institution_name: '',
        academic_year: '',
        family_income: '',
        category: '',
        marks_percentage: '',
        documents: null,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingApplication(null);
    setFormData({
      scholarship_type: '',
      course_name: '',
      institution_name: '',
      academic_year: '',
      family_income: '',
      category: '',
      marks_percentage: '',
      documents: null,
    });
  };

  const handleSubmit = () => {
    const submitData = new FormData();
    
    Object.keys(formData).forEach(key => {
      if (formData[key] !== null && formData[key] !== '') {
        submitData.append(key, formData[key]);
      }
    });

    if (editingApplication) {
      updateMutation.mutate({ id: editingApplication.id, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'pending':
        return 'warning';
      case 'under_review':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved':
        return <CheckCircle color="success" />;
      case 'rejected':
        return <Cancel color="error" />;
      case 'pending':
      case 'under_review':
        return <Schedule color="warning" />;
      default:
        return <Schedule />;
    }
  };

  const canEditApplication = (status) => {
    return ['draft', 'pending'].includes(status);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          My Applications
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
        >
          New Application
        </Button>
      </Box>

      {/* Applications List */}
      {isLoading ? (
        <Alert severity="info">Loading applications...</Alert>
      ) : applications && applications.length > 0 ? (
        <Grid container spacing={3}>
          {applications.map((application) => (
            <Grid item xs={12} key={application.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                      <Typography variant="h6" gutterBottom>
                        {application.scholarship_type || 'Scholarship Application'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Application ID: {application.id}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getStatusIcon(application.status)}
                      <Chip
                        label={application.status?.replace('_', ' ').toUpperCase()}
                        color={getStatusColor(application.status)}
                        size="small"
                      />
                    </Box>
                  </Box>

                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="body2" color="text.secondary">
                        Course: {application.course_name || 'N/A'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Institution: {application.institution_name || 'N/A'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Academic Year: {application.academic_year || 'N/A'}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Typography variant="body2" color="text.secondary">
                        Category: {application.category || 'N/A'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Family Income: ₹{application.family_income ? Number(application.family_income).toLocaleString() : 'N/A'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Marks: {application.marks_percentage || 'N/A'}%
                      </Typography>
                    </Grid>
                  </Grid>

                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Submitted: {new Date(application.created_at).toLocaleDateString()}
                  </Typography>

                  {application.status_message && (
                    <Alert severity="info" sx={{ mt: 2, mb: 2 }}>
                      {application.status_message}
                    </Alert>
                  )}

                  <Divider sx={{ my: 2 }} />

                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={() => {/* TODO: Implement view details */}}
                    >
                      View Details
                    </Button>
                    
                    {canEditApplication(application.status) && (
                      <Button
                        size="small"
                        startIcon={<Edit />}
                        onClick={() => handleOpenDialog(application)}
                      >
                        Edit
                      </Button>
                    )}
                    
                    {application.documents && (
                      <Button
                        size="small"
                        startIcon={<Download />}
                        onClick={() => {/* TODO: Implement download */}}
                      >
                        Download Documents
                      </Button>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No applications yet
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Start your scholarship journey by submitting your first application
            </Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => handleOpenDialog()}
            >
              Submit New Application
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Application Form Dialog */}
      <Dialog 
        open={openDialog} 
        onClose={handleCloseDialog} 
        maxWidth="md" 
        fullWidth
      >
        <DialogTitle>
          {editingApplication ? 'Edit Application' : 'New Scholarship Application'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Scholarship Type</InputLabel>
                <Select
                  value={formData.scholarship_type}
                  label="Scholarship Type"
                  onChange={(e) => setFormData(prev => ({...prev, scholarship_type: e.target.value}))}
                >
                  <MenuItem value="merit">Merit Based</MenuItem>
                  <MenuItem value="need">Need Based</MenuItem>
                  <MenuItem value="minority">Minority</MenuItem>
                  <MenuItem value="sc_st">SC/ST</MenuItem>
                  <MenuItem value="obc">OBC</MenuItem>
                  <MenuItem value="ews">EWS</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Course Name"
                value={formData.course_name}
                onChange={(e) => setFormData(prev => ({...prev, course_name: e.target.value}))}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Institution Name"
                value={formData.institution_name}
                onChange={(e) => setFormData(prev => ({...prev, institution_name: e.target.value}))}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Academic Year"
                placeholder="e.g., 2023-24"
                value={formData.academic_year}
                onChange={(e) => setFormData(prev => ({...prev, academic_year: e.target.value}))}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Family Income (Annual)"
                type="number"
                value={formData.family_income}
                onChange={(e) => setFormData(prev => ({...prev, family_income: e.target.value}))}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  value={formData.category}
                  label="Category"
                  onChange={(e) => setFormData(prev => ({...prev, category: e.target.value}))}
                >
                  <MenuItem value="general">General</MenuItem>
                  <MenuItem value="obc">OBC</MenuItem>
                  <MenuItem value="sc">SC</MenuItem>
                  <MenuItem value="st">ST</MenuItem>
                  <MenuItem value="ews">EWS</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Marks Percentage"
                type="number"
                inputProps={{ min: 0, max: 100 }}
                value={formData.marks_percentage}
                onChange={(e) => setFormData(prev => ({...prev, marks_percentage: e.target.value}))}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Box sx={{ border: '2px dashed #ccc', borderRadius: 1, p: 2, textAlign: 'center' }}>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => setFormData(prev => ({...prev, documents: e.target.files[0]}))}
                  style={{ display: 'none' }}
                  id="document-upload"
                />
                <label htmlFor="document-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<CloudUpload />}
                  >
                    Upload Documents
                  </Button>
                </label>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Upload supporting documents (PDF, JPG, PNG)
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={createMutation.isLoading || updateMutation.isLoading}
          >
            {editingApplication ? 'Update' : 'Submit'} Application
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default StudentApplications;
