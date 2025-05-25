import React, { useEffect, useState } from 'react';
import { 
  Container, Box, Typography, Button, Paper, Alert, Snackbar
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { authService, userService, shiftService } from '../services/api';
import ShiftGrid from '../components/ShiftGrid';

const DashboardPage = () => {
  const [user, setUser] = useState(null);
  const [shifts, setShifts] = useState([]);
  const [userPreferences, setUserPreferences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  // Add state for pending operations
  const [pendingOperations, setPendingOperations] = useState({});
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Check if user is authenticated
        const authResponse = await authService.checkAuth();
        if (!authResponse.data.authenticated) {
          navigate('/login');
          return;
        }

        // Get user data
        const userId = localStorage.getItem('user_id');
        if (!userId) {
          navigate('/setup');
          return;
        }

        const userResponse = await userService.getUser(userId);
        setUser(userResponse.data);

        // Get all shifts
        const allShiftsResponse = await shiftService.getShifts();
        setShifts(allShiftsResponse.data);
        
        // Get user's shifts to determine preferences
        const userShiftsResponse = await shiftService.getShifts({ user_id: userId });
        setUserPreferences(userShiftsResponse.data.map(shift => shift.id));
      } catch (error) {
        console.error('Error fetching data:', error);
        navigate('/login');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await authService.logout();
      localStorage.removeItem('user_id');
      localStorage.removeItem('username');
      navigate('/login');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  const handleTogglePreference = async (shiftId) => {
    if (!user) return;
    
    // Check if there's already a pending operation for this shift
    if (pendingOperations[shiftId]) return;
    
    // Create a unique operation ID
    const operationId = `toggle-${shiftId}-${Date.now()}`;
    
    // Update pending operations immediately
    setPendingOperations(prev => ({
      ...prev,
      [shiftId]: operationId
    }));
    
    // Determine if we're adding or removing the preference
    const isPreferred = userPreferences.includes(shiftId);
    
    // Optimistically update the UI immediately
    setUserPreferences(prev => 
      isPreferred 
        ? prev.filter(id => id !== shiftId) 
        : [...prev, shiftId]
    );
    
    // Use setTimeout to make the API call feel even more responsive
    // This allows the UI to update before the API call starts
    setTimeout(async () => {
      try {
        if (isPreferred) {
          // Remove user from shift
          await shiftService.removeUserFromShift(shiftId, user.id);
          setSnackbar({
            open: true,
            message: 'Successfully opted out of shift',
            severity: 'success'
          });
        } else {
          // Add user to shift
          await shiftService.addUserToShift({
            shift_id: shiftId,
            user_id: user.id
          });
          setSnackbar({
            open: true,
            message: 'Successfully opted in to shift',
            severity: 'success'
          });
        }
      } catch (error) {
        console.error('Error updating shift preference:', error);
        
        // Revert the optimistic update
        setUserPreferences(prev => 
          isPreferred 
            ? [...prev, shiftId]
            : prev.filter(id => id !== shiftId)
        );
        
        setSnackbar({
          open: true,
          message: 'Failed to update shift preference. Please try again.',
          severity: 'error'
        });
      } finally {
        // Clear the pending operation
        setPendingOperations(prev => {
          const newPending = { ...prev };
          delete newPending[shiftId];
          return newPending;
        });
      }
    }, 10); // Very short timeout to ensure UI updates first
  };

  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  if (loading) {
    return (
      <Container>
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="h5">Loading...</Typography>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Open Flair Festival Crew Dashboard
        </Typography>
        <Button variant="outlined" onClick={handleLogout}>
          Logout
        </Button>
      </Box>

      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          Welcome, {user?.username || 'Crew Member'}!
        </Typography>
        {user?.group && (
          <Typography variant="body1">
            You're part of group: <strong>{user.group.name}</strong>
          </Typography>
        )}
      </Paper>

      <Typography variant="h5" gutterBottom>
        Available Shifts
      </Typography>
      <Typography variant="body2" sx={{ mb: 2 }}>
        Click on a shift to toggle your preference (green = opted in, red = not selected).
      </Typography>
      
      <ShiftGrid 
        shifts={shifts} 
        userPreferences={userPreferences} 
        onTogglePreference={handleTogglePreference}
        pendingOperations={pendingOperations}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default DashboardPage;