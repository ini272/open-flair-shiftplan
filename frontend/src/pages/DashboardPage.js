import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
  Container, Box, Typography, Button, Paper, Alert, Snackbar, Tabs, Tab
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { authService, userService, shiftService } from '../services/api';
import ShiftGrid from '../components/ShiftGrid';
import CoordinatorView from '../components/CoordinatorView';

const DashboardPage = () => {
  const [user, setUser] = useState(null);
  const [allUsers, setAllUsers] = useState([]); // Add this for coordinator view
  const [shifts, setShifts] = useState([]);
  const [optedOutShifts, setOptedOutShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [pendingOperations, setPendingOperations] = useState({});
  const [currentTab, setCurrentTab] = useState(0); // Add tab state
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

        // Get all users (for coordinator view)
        const allUsersResponse = await userService.getUsers();
        setAllUsers(allUsersResponse.data);

        // Get all shifts
        const allShiftsResponse = await shiftService.getShifts();
        setShifts(allShiftsResponse.data);
        
        // Get user's opted-out shifts
        const optOutsResponse = await shiftService.getUserOptOuts(userId);
        setOptedOutShifts(optOutsResponse.data.map(shift => shift.id));
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

  // Memoize the available shifts calculation
  const availableShiftIds = useMemo(() => {
    return shifts.map(shift => shift.id).filter(id => !optedOutShifts.includes(id));
  }, [shifts, optedOutShifts]);

  // Use useCallback with all dependencies
  const handleTogglePreference = useCallback(async (shiftId) => {
    if (!user) return;
    
    // Check if there's already a pending operation for this shift
    if (pendingOperations[shiftId]) return;
    
    // Create a unique operation ID
    const operationId = `toggle-${shiftId}-${Date.now()}`;
    
    // Determine if the shift is currently opted out
    const isOptedOut = optedOutShifts.includes(shiftId);
    
    // Update state in a single batch if possible
    setPendingOperations(prev => ({
      ...prev,
      [shiftId]: operationId
    }));
    
    // Optimistically update the UI immediately
    setOptedOutShifts(prev => 
      isOptedOut 
        ? prev.filter(id => id !== shiftId) // Remove from opted-out list
        : [...prev, shiftId] // Add to opted-out list
    );
    
    // Make the API call immediately
    try {
      if (isOptedOut) {
        // Opt back in (remove from opted-out list)
        await shiftService.optInUser({
          shift_id: shiftId,
          user_id: user.id
        });
        setSnackbar({
          open: true,
          message: 'Successfully opted in to shift',
          severity: 'success'
        });
      } else {
        // Opt out
        await shiftService.optOutUser({
          shift_id: shiftId,
          user_id: user.id
        });
        setSnackbar({
          open: true,
          message: 'Successfully opted out of shift',
          severity: 'success'
        });
      }
    } catch (error) {
      console.error('Error updating shift preference:', error);
      
      // Revert the optimistic update
      setOptedOutShifts(prev => 
        isOptedOut 
          ? [...prev, shiftId] // Add back to opted-out list
          : prev.filter(id => id !== shiftId) // Remove from opted-out list
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
  }, [user, pendingOperations, optedOutShifts]);

  const handleCloseSnackbar = useCallback(() => {
    setSnackbar(prev => ({ ...prev, open: false }));
  }, []);

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
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

      {/* Tab Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab label="My Shifts" />
          <Tab label="Coordinator View" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {currentTab === 0 && (
        <Box>
          <Typography variant="h5" gutterBottom>
            Available Shifts
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Click on a shift to toggle your availability (green = available, red = not available).
          </Typography>
          
          <ShiftGrid 
            shifts={shifts} 
            userPreferences={availableShiftIds} 
            onTogglePreference={handleTogglePreference}
            pendingOperations={pendingOperations}
          />
        </Box>
      )}

      {currentTab === 1 && (
        <CoordinatorView 
          shifts={shifts} 
          users={allUsers}
        />
      )}

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