import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
  Container, Box, Typography, Button, Paper, Alert, Snackbar, Tabs, Tab, Stack, ToggleButton, ToggleButtonGroup, Link,
  Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
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
  const [isSavingLocationPreference, setIsSavingLocationPreference] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const navigate = useNavigate();

  const getShiftSlotKey = useCallback((shift) => {
    const start = new Date(shift.start_time);
    const end = new Date(shift.end_time);
    const dayKey = start.toISOString().split('T')[0];
    const timeKey = [
      start.getHours(),
      start.getMinutes(),
      end.getHours(),
      end.getMinutes(),
    ].join(':');

    return `${dayKey}-${timeKey}`;
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Check if user is authenticated
        const authResponse = await authService.checkAuth();
        if (!authResponse.data.authenticated) {
          navigate('/login');
          return;
        }
        const authRole = authResponse.data.role;
        const sessionUserId = authResponse.data.user_id;

        // Get user data
        const storedUserId = localStorage.getItem('user_id');
        const userId = sessionUserId || storedUserId;
        if (!userId) {
          localStorage.removeItem('user_id');
          localStorage.removeItem('username');
          navigate('/access');
          return;
        }

        if (!sessionUserId && storedUserId) {
          localStorage.removeItem('user_id');
          localStorage.removeItem('username');
          navigate('/access');
          return;
        }

        const userResponse = await userService.getUser(userId);
        setUser(userResponse.data);
        setLocationPreference(userResponse.data.location_preference || 'both');

        // Coordinator capabilities require both the coordinator account and coordinator session.
        const hasCoordinatorAccess = authRole === 'coordinator' && Boolean(userResponse.data.is_coordinator);
        setIsCoordinator(hasCoordinatorAccess);
        setCurrentTab(hasCoordinatorAccess ? 1 : 0);

        if (hasCoordinatorAccess) {
          const allUsersResponse = await userService.getUsers();
          setAllUsers(
            allUsersResponse.data.filter((entry) => entry.is_active && !entry.is_coordinator)
          );
        } else {
          setAllUsers([]);
        }

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
          const response = await groupService.getGroup(user.group_id);
          setUserGroup(response.data);
          setLocationPreference(response.data.location_preference || 'both');
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

  const handleDeleteAccount = useCallback(async () => {
    if (!user) {
      return;
    }

    setIsDeletingAccount(true);

    try {
      await userService.deleteUser(user.id);
      await authService.logout();
      localStorage.removeItem('user_id');
      localStorage.removeItem('username');
      navigate('/login');
    } catch (error) {
      console.error('Error deleting account:', error);
      setSnackbar({
        open: true,
        message: translations.account.deleteFailed,
        severity: 'error',
      });
    } finally {
      setIsDeletingAccount(false);
      setDeleteDialogOpen(false);
    }
  }, [navigate, user]);

  // Memoize the available shifts calculation
  const availableShiftIds = useMemo(() => {
    return shifts.map(shift => shift.id).filter(id => !optedOutShifts.includes(id));
  }, [shifts, optedOutShifts]);

  const handleLocationChange = useCallback(async (event, newLocation) => {
    if (!user || !newLocation || newLocation === locationPreference) {
      return;
    }

    const previousPreference = locationPreference;
    setLocationPreference(newLocation);
    setIsSavingLocationPreference(true);

    try {
      if (user.group_id) {
        const response = await groupService.updateGroup(user.group_id, {
          location_preference: newLocation,
        });
        setUserGroup(prev => ({
          ...(prev || {}),
          ...response.data,
        }));
      } else {
        const response = await userService.updateUser(user.id, {
          location_preference: newLocation,
        });
        setUser(response.data);
      }
    } catch (error) {
      console.error('Error updating location preference:', error);
      setLocationPreference(previousPreference);
      setSnackbar({
        open: true,
        message: translations.shifts.locationPreferenceUpdateFailed,
        severity: 'error'
      });
    } finally {
      setIsSavingLocationPreference(false);
    }
  }, [locationPreference, user]);

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
      const slotOutcomeMap = new Map();
      
      results.forEach((result, index) => {
        const processedShift = shiftsToProcess[index];
        const slotKey = getShiftSlotKey(processedShift.shift);
        const currentSlotOutcome = slotOutcomeMap.get(slotKey) || {
          total: 0,
          success: 0,
        };

        currentSlotOutcome.total += 1;

        if (result.status === 'fulfilled' && result.value.success) {
          successfulOperations.push(result.value);
          currentSlotOutcome.success += 1;
        } else {
          failedOperations.push(processedShift);
        }

        slotOutcomeMap.set(slotKey, currentSlotOutcome);
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
      const successCount = Array.from(slotOutcomeMap.values()).filter(
        (slotOutcome) => slotOutcome.success === slotOutcome.total
      ).length;
      const failCount = Array.from(slotOutcomeMap.values()).filter(
        (slotOutcome) => slotOutcome.success < slotOutcome.total
      ).length;
      const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('de-DE', {
          weekday: 'short',
          month: 'short',
          day: 'numeric'
        });
      };
      
      if (successCount > 0 && failCount === 0) {
        const successTemplate = shouldSelect
          ? translations.shifts.batchSelectSuccess
          : translations.shifts.batchDeselectSuccess;
        setSnackbar({
          open: true,
          message: successTemplate
            .replace('{count}', successCount)
            .replace('{day}', formatDate(day)),
          severity: 'success'
        });
      } else if (successCount > 0 && failCount > 0) {
        setSnackbar({
          open: true,
          message: translations.shifts.batchPartialSuccess
            .replace('{successCount}', successCount)
            .replace('{failCount}', failCount)
            .replace('{day}', formatDate(day)),
          severity: 'warning'
        });
      } else if (failCount > 0) {
        const failedTemplate = shouldSelect
          ? translations.shifts.batchSelectFailed
          : translations.shifts.batchDeselectFailed;
        setSnackbar({
          open: true,
          message: failedTemplate
            .replace('{count}', failCount)
            .replace('{day}', formatDate(day)),
          severity: 'error'
        });
      }
      
    } catch (error) {
      console.error('Batch operation failed:', error);
      setSnackbar({
        open: true,
        message: translations.shifts.batchOperationFailed,
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
  }, [getShiftSlotKey, optedOutShifts, user]);

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
          <Typography variant="h5">{translations.messages.loading}</Typography>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 2.5, md: 3 } }}>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Logo size="header" />

        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            color="error"
            size="small"
            onClick={() => setDeleteDialogOpen(true)}
          >
            {translations.account.deleteAccount}
          </Button>
          <Button variant="outlined" size="small" onClick={handleLogout}>
            {translations.logout}
          </Button>
        </Stack>
      </Box>

      {/* Tab Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2.5 }}>
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
          {isCoordinator && (
            <Alert severity="info" sx={{ mb: 2 }}>
              {translations.coordinator.coordinatorShiftSelectionDisabled}
            </Alert>
          )}

          <Box
            sx={isCoordinator ? {
              opacity: 0.5,
              pointerEvents: 'none',
              userSelect: 'none',
            } : undefined}
          >
          <Paper
            variant="outlined"
            sx={{
              mb: 2.5,
              px: { xs: 1.5, sm: 2 },
              py: 1.5,
              borderRadius: 3,
              boxShadow: 'none',
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>
              {translations.shifts.selectionTipsTitle}
            </Typography>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Box>
                <Box
                  component="ul"
                  sx={{
                    m: 0,
                    pl: 2.5,
                    color: 'text.secondary',
                    '& li + li': { mt: 0.75 },
                  }}
                >
                  <Box component="li">
                    <Typography variant="body2" component="span" color="text.secondary">
                      {translations.shifts.selectionIntroPrefix}{' '}
                    </Typography>
                    <Box
                      component="span"
                      sx={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        px: 0.75,
                        py: 0.1,
                        borderRadius: 1,
                        bgcolor: 'success.light',
                        color: 'success.contrastText',
                        fontWeight: 700,
                      }}
                    >
                      {translations.shifts.selectionColorAvailable}
                    </Box>{' '}
                    <Typography variant="body2" component="span" color="text.secondary">
                      {translations.shifts.selectionIntroMiddle}
                    </Typography>
                  </Box>

                  <Box component="li">
                    <Typography variant="body2" component="span" color="text.secondary">
                      {translations.shifts.selectionTogglePrefix}{' '}
                    </Typography>
                    <Box
                      component="span"
                      sx={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        px: 0.75,
                        py: 0.1,
                        borderRadius: 1,
                        bgcolor: 'error.light',
                        color: 'error.contrastText',
                        fontWeight: 700,
                      }}
                    >
                      {translations.shifts.selectionColorUnavailable}
                    </Box>{' '}
                    <Typography variant="body2" component="span" color="text.secondary">
                      {translations.shifts.selectionToggleSuffix}
                    </Typography>
                  </Box>

                  <Box component="li">
                    <Typography variant="body2" component="span" color="text.secondary">
                      {translations.shifts.selectionHintSchedulePrefix}{' '}
                    </Typography>
                    <Link
                      href="https://www.open-flair.de/2026/timetable"
                      target="_blank"
                      rel="noopener noreferrer"
                      underline="hover"
                      sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, fontWeight: 600 }}
                    >
                      {translations.shifts.selectionHintScheduleLink}
                      <OpenInNewIcon sx={{ fontSize: 14 }} />
                    </Link>
                    <Typography variant="body2" component="span" color="text.secondary">
                      .
                    </Typography>
                  </Box>
                </Box>
              </Box>

              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
                  {translations.shifts.selectionAutoTitle}
                </Typography>
                <Box
                  component="ul"
                  sx={{
                    m: 0,
                    pl: 2.5,
                    color: 'text.secondary',
                    '& li + li': { mt: 0.75 },
                  }}
                >
                  <Box component="li">
                    <Typography variant="body2" color="text.secondary">
                      {translations.shifts.selectionPlannerFairness}
                    </Typography>
                  </Box>
                  <Box component="li">
                    <Typography variant="body2" color="text.secondary">
                      {translations.shifts.selectionPlannerOnlyGreen}
                    </Typography>
                  </Box>
                  <Box component="li">
                    <Typography variant="body2" color="text.secondary">
                      {translations.shifts.selectionPlannerWeekend}
                    </Typography>
                  </Box>
                  <Box component="li">
                    <Typography variant="body2" color="text.secondary">
                      {translations.shifts.selectionPlannerMaxShifts}
                    </Typography>
                  </Box>
                </Box>

                <Box
                  sx={{
                    mt: 1.5,
                    px: 0.25,
                    color: 'success.dark',
                  }}
                >
                  <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                    {translations.shifts.selectionPlannerKeepGreen}
                  </Typography>
                </Box>
              </Box>
            </Stack>
          </Paper>

          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              {translations.shifts.locationPreferenceTitle}
            </Typography>
            <ToggleButtonGroup
              value={locationPreference}
              exclusive
              onChange={handleLocationChange}
              aria-label={translations.shifts.locationPreferenceTitle}
              sx={{ mb: 2 }}
              disabled={isSavingLocationPreference}
            >
              <ToggleButton value="both">
                {translations.shifts.locationPreferenceBoth}
              </ToggleButton>
              <ToggleButton value="weinzelt">
                {translations.shifts.locationPreferenceWeinzelt}
              </ToggleButton>
              <ToggleButton value="bierwagen">
                {translations.shifts.locationPreferenceBierwagen}
              </ToggleButton>
            </ToggleButtonGroup>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.25 }}>
              {translations.shifts.locationPreferenceHelper}
            </Typography>

            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              sx={{ color: 'text.secondary' }}
            >
              <InfoOutlinedIcon sx={{ fontSize: 18 }} />
              <Typography variant="body2">
                {translations.shifts.selectionAutoSave}
              </Typography>
            </Stack>
          </Box>
          
          <ShiftGrid 
            shifts={shifts} 
            userPreferences={availableShiftIds} 
            pendingOperations={pendingOperations}
            onBatchDayToggle={handleBatchDayToggle}
            batchPendingDays={batchPendingDays}
          />
          </Box>
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

      <Dialog
        open={deleteDialogOpen}
        onClose={() => !isDeletingAccount && setDeleteDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>{translations.account.deleteAccount}</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            {translations.account.deleteAccountConfirm}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={isDeletingAccount}>
            {translations.cancel}
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleDeleteAccount}
            disabled={isDeletingAccount}
            startIcon={isDeletingAccount ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {isDeletingAccount ? translations.account.deletingAccount : translations.account.deleteAccount}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default DashboardPage;
