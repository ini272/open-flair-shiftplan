import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
  Container, Box, Typography, Button, Paper, Alert, Snackbar, Tabs, Tab, Stack, ToggleButton, ToggleButtonGroup, Link,
  Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';
import { useNavigate } from 'react-router-dom';
import { authService, userService, shiftService } from '../services/api';
import ShiftGrid from '../components/ShiftGrid';
import CoordinatorView from '../components/CoordinatorView';
import ParticipantAssignments from '../components/ParticipantAssignments';
import Logo from '../components/Logo';
import { translations } from '../utils/translations';
import { isUnder16RestrictedShift } from '../utils/shiftRestrictions';
import { groupService } from '../services/api';


const DashboardPage = () => {
  const [user, setUser] = useState(null);
  const [allUsers, setAllUsers] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [optedOutShifts, setOptedOutShifts] = useState([]);
  const [savedOptedOutShifts, setSavedOptedOutShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCoordinator, setIsCoordinator] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [isSavingAvailability, setIsSavingAvailability] = useState(false);
  const [availabilitySaveNotice, setAvailabilitySaveNotice] = useState(false);
  const [currentTab, setCurrentTab] = useState(0);
  const [userGroup, setUserGroup] = useState(null);
  const [locationPreference, setLocationPreference] = useState('both');
  const [isSavingLocationPreference, setIsSavingLocationPreference] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [participantPlan, setParticipantPlan] = useState({ is_released: false, assignments: [] });
  const [isLoadingParticipantPlan, setIsLoadingParticipantPlan] = useState(false);
  const [participantPlanError, setParticipantPlanError] = useState(false);
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
        const optOutShiftIds = optOutsResponse.data.map((shift) => shift.id);
        setOptedOutShifts(optOutShiftIds);
        setSavedOptedOutShifts(optOutShiftIds);
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

  const loadParticipantPlan = useCallback(async () => {
    if (!user || isCoordinator) {
      return;
    }

    setIsLoadingParticipantPlan(true);
    setParticipantPlanError(false);

    try {
      const response = await shiftService.getMyAssignments();
      setParticipantPlan(response.data);
    } catch (error) {
      console.error('Error loading participant plan:', error);
      setParticipantPlanError(true);
    } finally {
      setIsLoadingParticipantPlan(false);
    }
  }, [isCoordinator, user]);

  useEffect(() => {
    if (currentTab === 1 && !isCoordinator) {
      loadParticipantPlan();
    }
  }, [currentTab, isCoordinator, loadParticipantPlan]);

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
    return shifts
      .filter((shift) => !(user?.is_under_16 && isUnder16RestrictedShift(shift)))
      .map((shift) => shift.id)
      .filter((id) => !optedOutShifts.includes(id));
  }, [optedOutShifts, shifts, user?.is_under_16]);

  const blockedShiftIdSet = useMemo(() => (
    new Set(
      shifts
        .filter((shift) => user?.is_under_16 && isUnder16RestrictedShift(shift))
        .map((shift) => shift.id)
    )
  ), [shifts, user?.is_under_16]);

  const participantViewOption = useMemo(() => {
    if (!user) {
      return null;
    }

    if (user.group_id) {
      return {
        id: user.group_id,
        type: 'group',
        label: userGroup?.name || 'Mein Team',
      };
    }

    return {
      id: user.id,
      type: 'user',
      label: user.username,
      isUnder16: Boolean(user.is_under_16),
    };
  }, [user, userGroup]);

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

  const hasUnsavedAvailabilityChanges = useMemo(() => {
    const currentOptOuts = new Set(optedOutShifts);
    const savedOptOuts = new Set(savedOptedOutShifts);

    return currentOptOuts.size !== savedOptOuts.size || [...currentOptOuts].some(
      (shiftId) => !savedOptOuts.has(shiftId)
    );
  }, [optedOutShifts, savedOptedOutShifts]);

  const handleBatchDayToggle = useCallback((dayShifts, shouldSelect) => {
    const actionableDayShifts = dayShifts.filter((shift) => !blockedShiftIdSet.has(shift.id));
    if (actionableDayShifts.length === 0) {
      return;
    }

    setAvailabilitySaveNotice(false);
    setOptedOutShifts((previousOptOuts) => {
      const updatedOptOuts = new Set(previousOptOuts);

      for (const shift of actionableDayShifts) {
        if (shouldSelect) {
          updatedOptOuts.delete(shift.id);
        } else {
          updatedOptOuts.add(shift.id);
        }
      }

      return [...updatedOptOuts];
    });
  }, [blockedShiftIdSet]);

  const handleDiscardAvailabilityChanges = useCallback(() => {
    setOptedOutShifts(savedOptedOutShifts);
    setAvailabilitySaveNotice(false);
  }, [savedOptedOutShifts]);

  const handleSaveAvailability = useCallback(async () => {
    if (!user || isSavingAvailability || !hasUnsavedAvailabilityChanges) {
      return;
    }

    const currentOptOuts = new Set(optedOutShifts);
    const savedOptOuts = new Set(savedOptedOutShifts);
    const changedShiftIds = new Set([...currentOptOuts, ...savedOptOuts]);
    const changes = [...changedShiftIds]
      .filter((shiftId) => currentOptOuts.has(shiftId) !== savedOptOuts.has(shiftId))
      .map((shiftId) => ({
        shift_id: shiftId,
        is_available: !currentOptOuts.has(shiftId),
      }));

    if (changes.length === 0) {
      return;
    }

    setIsSavingAvailability(true);

    try {
      await shiftService.saveAvailability({
        ...(user.group_id ? { group_id: user.group_id } : { user_id: user.id }),
        changes,
      });

      setSavedOptedOutShifts([...currentOptOuts]);
      setAvailabilitySaveNotice(true);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      console.error('Error saving availability:', error);
      setSnackbar({
        open: true,
        message: translations.shifts.saveSelectionFailed,
        severity: 'error',
      });
    } finally {
      setIsSavingAvailability(false);
    }
  }, [hasUnsavedAvailabilityChanges, isSavingAvailability, optedOutShifts, savedOptedOutShifts, user]);

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
          {!isCoordinator && (
            <Tab label={translations.shifts.myAssignments} />
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

          {user?.is_under_16 && (
            <Alert severity="info" sx={{ mb: 2 }}>
              {translations.restrictions.under16EveningShift}
            </Alert>
          )}

          {availabilitySaveNotice && (
            <Alert
              severity="success"
              sx={{ mb: 2 }}
              onClose={() => setAvailabilitySaveNotice(false)}
            >
              {translations.shifts.selectionSaved}
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
              sx={(theme) => ({
                mb: 2,
                borderRadius: 2,
                overflow: 'hidden',
                boxShadow: '0 1px 2px rgba(15, 23, 42, 0.08)',
                '& .MuiToggleButtonGroup-grouped': {
                  px: 1.75,
                  py: 0.95,
                  minHeight: 46,
                  border: `2px solid ${theme.palette.divider} !important`,
                  borderRadius: '0 !important',
                  fontWeight: 700,
                  textTransform: 'none',
                },
                '& .MuiToggleButtonGroup-grouped:not(:first-of-type)': {
                  marginLeft: '-2px',
                },
                '& .Mui-selected': {
                  backgroundColor: theme.palette.primary.light,
                  color: theme.palette.primary.contrastText,
                  borderColor: `${theme.palette.primary.main} !important`,
                },
                '& .MuiToggleButtonGroup-grouped:first-of-type': {
                  borderTopLeftRadius: theme.spacing(1.5),
                  borderBottomLeftRadius: theme.spacing(1.5),
                },
                '& .MuiToggleButtonGroup-grouped:last-of-type': {
                  borderTopRightRadius: theme.spacing(1.5),
                  borderBottomRightRadius: theme.spacing(1.5),
                },
              })}
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
                {translations.shifts.selectionSaveHint}
              </Typography>
            </Stack>
          </Box>

          <Paper
            variant="outlined"
            sx={(theme) => ({
              mb: 2.5,
              p: { xs: 1.5, sm: 2 },
              borderRadius: 3,
              borderColor: hasUnsavedAvailabilityChanges
                ? theme.palette.warning.main
                : theme.palette.divider,
              backgroundColor: hasUnsavedAvailabilityChanges
                ? theme.palette.warning.light
                : 'background.paper',
            })}
          >
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1.5}
              justifyContent="space-between"
              alignItems={{ sm: 'center' }}
            >
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {hasUnsavedAvailabilityChanges
                    ? translations.shifts.selectionUnsavedChanges
                    : translations.shifts.selectionNoUnsavedChanges}
                </Typography>
                {hasUnsavedAvailabilityChanges && (
                  <Typography variant="body2" color="text.secondary">
                    {translations.shifts.selectionSaveHint}
                  </Typography>
                )}
              </Box>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1}
                sx={{ width: { xs: '100%', sm: 'auto' } }}
              >
                <Button
                  variant="outlined"
                  onClick={handleDiscardAvailabilityChanges}
                  disabled={!hasUnsavedAvailabilityChanges || isSavingAvailability}
                  startIcon={<RestartAltIcon />}
                  fullWidth
                >
                  {translations.shifts.discardSelectionChanges}
                </Button>
                <Button
                  variant="contained"
                  onClick={handleSaveAvailability}
                  disabled={!hasUnsavedAvailabilityChanges || isSavingAvailability}
                  startIcon={
                    isSavingAvailability
                      ? <CircularProgress size={16} color="inherit" />
                      : <SaveOutlinedIcon />
                  }
                  fullWidth
                >
                  {isSavingAvailability
                    ? translations.shifts.savingSelection
                    : translations.shifts.saveSelection}
                </Button>
              </Stack>
            </Stack>
          </Paper>

          <ShiftGrid
            shifts={shifts}
            userPreferences={availableShiftIds}
            blockedShiftIds={Array.from(blockedShiftIdSet)}
            onBatchDayToggle={handleBatchDayToggle}
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

      {currentTab === 1 && !isCoordinator && (
        <ParticipantAssignments
          plan={participantPlan}
          isLoading={isLoadingParticipantPlan}
          error={participantPlanError}
          onRefresh={loadParticipantPlan}
          shifts={shifts}
          selectedViewOption={participantViewOption}
          optedOutShifts={optedOutShifts}
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
