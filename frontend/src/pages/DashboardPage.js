import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
  Container, Box, Typography, Button, Paper, Alert, Snackbar, Tabs, Tab, Link, Stack, Chip, ToggleButton, ToggleButtonGroup
} from '@mui/material';
import { 
  OpenInNew as OpenInNewIcon,
  Schedule as ScheduleIcon 
} from '@mui/icons-material';
import PersonIcon from '@mui/icons-material/Person';
import { useNavigate } from 'react-router-dom';
import { authService, userService, shiftService } from '../services/api';
import ShiftGrid from '../components/ShiftGrid';
import CoordinatorView from '../components/CoordinatorView';
import Logo from '../components/Logo';
import { translations } from '../utils/translations';
import { groupService } from '../services/api';


const DashboardPage = () => {
  const [user, setUser] = useState(null);
  const [allUsers, setAllUsers] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [optedOutShifts, setOptedOutShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCoordinator, setIsCoordinator] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [pendingOperations, setPendingOperations] = useState({});
  const [batchPendingDays, setBatchPendingDays] = useState({}); // New state for batch operations
  const [currentTab, setCurrentTab] = useState(0);
  const [userGroup, setUserGroup] = useState(null);
  const [locationPreference, setLocationPreference] = useState('both');
  const navigate = useNavigate();

  // Add this helper function at the top of the component:
  const getShiftLocation = (shiftTitle) => {
    const title = shiftTitle.toLowerCase();
    if (title.includes('weinzelt')) return 'weinzelt';
    if (title.includes('bierwagen')) return 'bierwagen';
    return 'unknown';
  };

  // Add this handler function:
  const handleLocationChange = async (event, newLocation) => {
    if (!newLocation) return; // Prevent deselecting all options
    
    setLocationPreference(newLocation);
    
    if (newLocation === 'both') {
      // Simple approach: Opt in to ALL shifts (make everything green)
      const allShifts = shifts.filter(shift => {
        const shiftLocation = getShiftLocation(shift.title);
        return shiftLocation === 'weinzelt' || shiftLocation === 'bierwagen';
      });
      
      if (allShifts.length > 0) {
        await handleBatchDayToggle(allShifts, true); // Opt in to everything
      }
    } else {
      // Filter shifts by location and batch opt-out from unwanted location
      const targetLocation = newLocation;
      const shiftsToOptOut = shifts.filter(shift => {
        const shiftLocation = getShiftLocation(shift.title);
        return shiftLocation !== targetLocation && shiftLocation !== 'unknown';
      });
      
      const shiftsToOptIn = shifts.filter(shift => {
        const shiftLocation = getShiftLocation(shift.title);
        return shiftLocation === targetLocation;
      });
      
      // Batch opt-out from unwanted location
      if (shiftsToOptOut.length > 0) {
        await handleBatchDayToggle(shiftsToOptOut, false);
      }
      
      // Batch opt-in to preferred location
      if (shiftsToOptIn.length > 0) {
        await handleBatchDayToggle(shiftsToOptIn, true);
      }
    }
  };

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

        // Check coordinator status from user data
        setIsCoordinator(userResponse.data.is_coordinator || false);

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

  useEffect(() => {
    const fetchUserGroup = async () => {
      if (user?.group_id && !userGroup) {
        try {
          console.log('Fetching group details for group_id:', user.group_id);
          const response = await groupService.getGroup(user.group_id);
          console.log('Group details:', response.data);
          setUserGroup(response.data);
        } catch (error) {
          console.error('Error fetching user group:', error);
        }
      }
    };
    
    fetchUserGroup();
  }, [user?.group_id, userGroup]);

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
      if (user.group_id) {
        // User is in a group - use group opt-out endpoints
        if (isOptedOut) {
          // Opt back in (remove from opted-out list)
          await shiftService.optInGroup({
            shift_id: shiftId,
            group_id: user.group_id
          });
          setSnackbar({
            open: true,
            message: `Gruppe wieder für Schicht verfügbar`,
            severity: 'success'
          });
        } else {
          // Opt out
          await shiftService.optOutGroup({
            shift_id: shiftId,
            group_id: user.group_id
          });
          setSnackbar({
            open: true,
            message: `Gruppe von Schicht abgemeldet`,
            severity: 'success'
          });
        }
      } else {
        // Individual user - use individual opt-out endpoints
        if (isOptedOut) {
          // Opt back in (remove from opted-out list)
          await shiftService.optInUser({
            shift_id: shiftId,
            user_id: user.id
          });
          setSnackbar({
            open: true,
            message: translations.shifts.optedInSuccess,
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
            message: translations.shifts.optedOutSuccess,
            severity: 'success'
          });
        }
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
        message: error.response?.data?.detail || translations.shifts.updateFailed,
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

  // New batch day toggle handler
  const handleBatchDayToggle = useCallback(async (dayShifts, shouldSelect) => {
    if (!user || dayShifts.length === 0) return;
    
    // Get the day from the first shift for tracking
    const day = new Date(dayShifts[0].start_time).toISOString().split('T')[0];
    
    // Set day as pending
    setBatchPendingDays(prev => ({ ...prev, [day]: true }));
    
    try {
      const operations = [];
      const shiftsToProcess = [];
      
      for (const shift of dayShifts) {
        const isCurrentlyOptedOut = optedOutShifts.includes(shift.id);
        const isCurrentlySelected = !isCurrentlyOptedOut;
        
        // Only process if the action is needed
        if (shouldSelect && !isCurrentlySelected) {
          shiftsToProcess.push({ shift, action: 'opt_in' });
        } else if (!shouldSelect && isCurrentlySelected) {
          shiftsToProcess.push({ shift, action: 'opt_out' });
        }
      }
      
      // Set pending state for all shifts being processed
      const pendingShiftIds = shiftsToProcess.map(item => item.shift.id);
      setPendingOperations(prev => {
        const updated = { ...prev };
        pendingShiftIds.forEach(id => {
          updated[id] = `batch-${day}-${Date.now()}`;
        });
        return updated;
      });
      
      // Optimistically update the UI
      setOptedOutShifts(prev => {
        let updated = [...prev];
        shiftsToProcess.forEach(({ shift, action }) => {
          if (action === 'opt_in') {
            updated = updated.filter(id => id !== shift.id);
          } else if (action === 'opt_out') {
            if (!updated.includes(shift.id)) {
              updated.push(shift.id);
            }
          }
        });
        return updated;
      });
      
      // Process all shifts simultaneously
      for (const { shift, action } of shiftsToProcess) {
        if (action === 'opt_in') {
          operations.push(
            user.group_id ? 
              shiftService.optInGroup({
                shift_id: shift.id,
                group_id: user.group_id
              }).then(() => ({ shiftId: shift.id, action: 'opt_in', success: true }))
                .catch(error => ({ shiftId: shift.id, action: 'opt_in', success: false, error }))
            :
              shiftService.optInUser({
                shift_id: shift.id,
                user_id: user.id
              }).then(() => ({ shiftId: shift.id, action: 'opt_in', success: true }))
                .catch(error => ({ shiftId: shift.id, action: 'opt_in', success: false, error }))
          );
        } else {
          operations.push(
            user.group_id ?
              shiftService.optOutGroup({
                shift_id: shift.id,
                group_id: user.group_id
              }).then(() => ({ shiftId: shift.id, action: 'opt_out', success: true }))
                .catch(error => ({ shiftId: shift.id, action: 'opt_out', success: false, error }))
            :
              shiftService.optOutUser({
                shift_id: shift.id,
                user_id: user.id
              }).then(() => ({ shiftId: shift.id, action: 'opt_out', success: true }))
                .catch(error => ({ shiftId: shift.id, action: 'opt_out', success: false, error }))
          );
        }
      }
      
      // Wait for all operations to complete
      const results = await Promise.allSettled(operations);
      
      // Process results
      const successfulOperations = [];
      const failedOperations = [];
      
      results.forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value.success) {
          successfulOperations.push(result.value);
        } else {
          failedOperations.push(shiftsToProcess[index]);
        }
      });
      
      // Revert failed operations in the UI
      if (failedOperations.length > 0) {
        setOptedOutShifts(prev => {
          let updated = [...prev];
          failedOperations.forEach(({ shift, action }) => {
            if (action === 'opt_in') {
              // Revert: add back to opted-out list
              if (!updated.includes(shift.id)) {
                updated.push(shift.id);
              }
            } else if (action === 'opt_out') {
              // Revert: remove from opted-out list
              updated = updated.filter(id => id !== shift.id);
            }
          });
          return updated;
        });
      }
      
      // Clear pending state for processed shifts
      setPendingOperations(prev => {
        const updated = { ...prev };
        pendingShiftIds.forEach(id => {
          delete updated[id];
        });
        return updated;
      });
      
      // Show results
      const successCount = successfulOperations.length;
      const failCount = failedOperations.length;
      const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('de-DE', {
          weekday: 'short',
          month: 'short',
          day: 'numeric'
        });
      };
      
      if (successCount > 0 && failCount === 0) {
        const action = shouldSelect ? 'ausgewählt' : 'abgewählt';
        setSnackbar({
          open: true,
          message: `${successCount} ${translations.shifts.batchSelectSuccess.replace('{day}', formatDate(day))}`,
          severity: 'success'
        });
      } else if (successCount > 0 && failCount > 0) {
        setSnackbar({
          open: true,
          message: `${successCount} shifts updated, ${failCount} failed for ${formatDate(day)}`,
          severity: 'warning'
        });
      } else if (failCount > 0) {
        setSnackbar({
          open: true,
          message: `Failed to update ${failCount} shifts for ${formatDate(day)}`,
          severity: 'error'
        });
      }
      
    } catch (error) {
      console.error('Batch operation failed:', error);
      setSnackbar({
        open: true,
        message: 'Batch operation failed',
        severity: 'error'
      });
    } finally {
      // Clear day pending state
      setBatchPendingDays(prev => {
        const updated = { ...prev };
        delete updated[day];
        return updated;
      });
    }
  }, [user, optedOutShifts]);

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
          <Typography variant="h5">{translations.loading}</Typography>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {/* Logo + Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Logo size="large" />
          <Typography variant="h4" component="h1">
            {translations.festival.crewDashboard}
          </Typography>
        </Box>
        
        <Button variant="outlined" onClick={handleLogout}>
          {translations.logout}
        </Button>
      </Box>

      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          {translations.account.welcome}, {user?.username || 'Crew Member'}!
        </Typography>
        {user?.group_id && userGroup && (
          <Box>
            <Typography variant="body1" sx={{ mb: 2 }}>
              <strong>Team:</strong> {userGroup.name}
            </Typography>
            {userGroup.users && userGroup.users.length > 1 && (
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Teammitglieder:
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {userGroup.users
                    .map(member => (
                      <Chip
                        key={member.id}
                        icon={<PersonIcon />}
                        label={member.id === user.id ? `${member.username} (Du)` : member.username}
                        size="small"
                        variant={member.id === user.id ? "filled" : "outlined"}
                        color={member.id === user.id ? "primary" : "secondary"}
                      />
                    ))}
                </Stack>
              </Box>
            )}
          </Box>
        )}
      </Paper>

      {/* Tab Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab label={translations.shifts.myShifts} />
          {isCoordinator && (
            <Tab label={translations.shifts.coordinatorView} />
          )}
        </Tabs>
      </Box>

      {/* Tab Content */}
      {currentTab === 0 && (
        <Box>
          {/* Festival Timetable Link */}
          <Paper sx={{ p: 2, mb: 3, backgroundColor: 'primary.main', color: 'white' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">
                {translations.shifts.myShifts} - {translations.festival.name} {translations.festival.year}
              </Typography>
              <Link
                href="https://www.open-flair.de/2025/timetable"
                target="_blank"
                rel="noopener noreferrer"
                sx={{ 
                  color: 'white', 
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  '&:hover': {
                    textDecoration: 'underline'
                  }
                }}
              >
                <ScheduleIcon />
                <Typography variant="body1">
                  {translations.festival.timetable}
                </Typography>
                <OpenInNewIcon fontSize="small" />
              </Link>
            </Box>
            <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
              {translations.festival.dates} • {translations.festival.location}
            </Typography>
          </Paper>

          <Typography variant="h5" gutterBottom>
            {translations.shifts.availableShifts}
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {translations.shifts.clickToToggle}
          </Typography>
          
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Standort-Präferenz
            </Typography>
            <ToggleButtonGroup
              value={locationPreference}
              exclusive
              onChange={handleLocationChange}
              aria-label="location preference"
              sx={{ mb: 2 }}
            >
              <ToggleButton value="both">
                Beide Standorte
              </ToggleButton>
              <ToggleButton value="weinzelt">
                Nur Weinzelt
              </ToggleButton>
              <ToggleButton value="bierwagen">
                Nur Bierwagen
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
          
          <ShiftGrid 
            shifts={shifts} 
            userPreferences={availableShiftIds} 
            onTogglePreference={handleTogglePreference}
            pendingOperations={pendingOperations}
            onBatchDayToggle={handleBatchDayToggle}
            batchPendingDays={batchPendingDays}
          />
        </Box>
      )}

      {currentTab === 1 && isCoordinator && (
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

// Add this function with the other handlers:
const handleBatchToggle = async (shiftsToToggle, shouldSelect) => {
  if (!shiftsToToggle || shiftsToToggle.length === 0) return;
  
  // Set pending state for all shifts
  const newPending = {};
  shiftsToToggle.forEach(shift => {
    newPending[shift.id] = true;
  });
  setPendingOperations(prev => ({ ...prev, ...newPending }));
  
  try {
    // Process shifts in batches to avoid overwhelming the API
    const batchSize = 5;
    for (let i = 0; i < shiftsToToggle.length; i += batchSize) {
      const batch = shiftsToToggle.slice(i, i + batchSize);
      const promises = batch.map(shift => {
        const isCurrentlySelected = availableShiftIds.includes(shift.id);
        
        if (shouldSelect && !isCurrentlySelected) {
          // Opt in to shift
          return preferenceService.setPreference({
            user_id: user.id,
            shift_id: shift.id,
            can_work: true
          });
        } else if (!shouldSelect && isCurrentlySelected) {
          // Opt out of shift
          return preferenceService.setPreference({
            user_id: user.id,
            shift_id: shift.id,
            can_work: false
          });
        }
        return Promise.resolve(); // No change needed
      });
      
      await Promise.all(promises);
    }
    
    // Refresh data
    await loadUserPreferences();
    
  } catch (error) {
    console.error('Error in batch toggle:', error);
    setError('Failed to update preferences');
  } finally {
    // Clear pending state
    const clearedPending = {};
    shiftsToToggle.forEach(shift => {
      clearedPending[shift.id] = undefined;
    });
    setPendingOperations(prev => ({ ...prev, ...clearedPending }));
  }
};

export default DashboardPage;