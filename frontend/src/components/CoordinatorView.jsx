import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import CoordinatorShiftGrid from './CoordinatorShiftGrid';
import CoordinatorPersonView from './CoordinatorPersonView';
import { groupService, shiftService } from '../services/api';
import { buildTeamColorMap, getTeamColor } from '../utils/teamColors';
import { translations } from '../utils/translations';

const ActionBar = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(1.25, 1.5),
  borderRadius: theme.spacing(2.5),
  border: `1px solid ${theme.palette.divider}`,
  boxShadow: 'none',
}));

const formatSelectionLabel = (option) => {
  if (!option) {
    return '';
  }

  return `${option.label} (${option.shiftCount ?? 0})`;
};

const CoordinatorView = ({ shifts, users }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentAssignments, setCurrentAssignments] = useState(null);
  const [plannerSummary, setPlannerSummary] = useState(null);
  const [error, setError] = useState(null);
  const [maxShiftsPerUser, setMaxShiftsPerUser] = useState(10);
  const [viewMode, setViewMode] = useState('day');
  const [selectedViewKey, setSelectedViewKey] = useState('');
  const [userOptOuts, setUserOptOuts] = useState({});
  const [groupOptions, setGroupOptions] = useState([]);
  const [teamDirectory, setTeamDirectory] = useState([]);
  const [groupOptOuts, setGroupOptOuts] = useState({});
  const [loadingSelectionContext, setLoadingSelectionContext] = useState(false);
  const [selectionContextLoaded, setSelectionContextLoaded] = useState(false);
  const registeredPeopleCount = users?.length || 0;

  useEffect(() => {
    const loadCurrentAssignments = async () => {
      try {
        const response = await shiftService.getCurrentAssignments();
        setPlannerSummary(response.data.planner || null);

        if (response.data.assignments && response.data.assignments.length > 0) {
          setCurrentAssignments(response.data.assignments);
        } else {
          setCurrentAssignments(null);
        }
      } catch (loadError) {
        console.log('No existing assignments or error loading:', loadError.message);
      }
    };

    loadCurrentAssignments();
  }, []);

  useEffect(() => {
    const loadTeamDirectory = async () => {
      try {
        const groupsResponse = await groupService.getGroups();
        setTeamDirectory(groupsResponse.data.filter((group) => group.is_active));
      } catch (loadError) {
        console.log('Failed to load team directory:', loadError);
      }
    };

    loadTeamDirectory();
  }, []);

  const ensureSelectionContextLoaded = useCallback(async () => {
    if (loadingSelectionContext || selectionContextLoaded || !users || users.length === 0) {
      return;
    }

    setLoadingSelectionContext(true);

    try {
      const selectableUsers = (users || []).filter((user) => !user.group_id);
      const userOptOutResults = await Promise.all(
        selectableUsers.map(async (user) => {
          try {
            const response = await shiftService.getUserOptOuts(user.id);
            return { userId: user.id, optOuts: response.data };
          } catch (loadError) {
            console.log(`Failed to load opt-outs for user ${user.id}:`, loadError);
            return { userId: user.id, optOuts: [] };
          }
        })
      );

      const nextUserOptOuts = {};
      userOptOutResults.forEach(({ userId, optOuts }) => {
        nextUserOptOuts[userId] = optOuts;
      });
      setUserOptOuts(nextUserOptOuts);

      try {
        const groupsResponse = await groupService.getGroups();
        const activeGroups = groupsResponse.data.filter((group) => group.is_active);

        const groupDetails = await Promise.all(
          activeGroups.map(async (group) => {
            try {
              const [groupDetailResponse, groupOptOutResponse] = await Promise.all([
                groupService.getGroup(group.id),
                shiftService.getGroupOptOuts(group.id),
              ]);

              return {
                group: groupDetailResponse.data,
                optOuts: groupOptOutResponse.data,
              };
            } catch (loadError) {
              console.log(`Failed to load group context for ${group.id}:`, loadError);
              return {
                group: { ...group, users: [] },
                optOuts: [],
              };
            }
          })
        );

        setGroupOptions(
          groupDetails
            .map(({ group }) => group)
            .filter((group) => group.users && group.users.length > 0 && group.users.every((user) => !user.is_coordinator))
        );

        const nextGroupOptOuts = {};
        groupDetails.forEach(({ group, optOuts }) => {
          nextGroupOptOuts[group.id] = optOuts;
        });
        setGroupOptOuts(nextGroupOptOuts);
      } catch (loadError) {
        console.log('Failed to load groups:', loadError);
      }

      setSelectionContextLoaded(true);
    } finally {
      setLoadingSelectionContext(false);
    }
  }, [loadingSelectionContext, selectionContextLoaded, users]);

  useEffect(() => {
    if (viewMode === 'person') {
      ensureSelectionContextLoaded();
    }
  }, [ensureSelectionContextLoaded, viewMode]);

  const handleGeneratePlan = async () => {
    setIsGenerating(true);
    setError(null);

    try {
      const response = await shiftService.generatePlan(maxShiftsPerUser);
      setCurrentAssignments(response.data.assignments);
      setPlannerSummary(response.data.planner || null);
    } catch (generationError) {
      console.error('Detailed error:', generationError);
      setError(translations.coordinator.planGenerationFailed);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleResetAllAssignments = async () => {
    try {
      await shiftService.clearAllAssignments();
      setCurrentAssignments(null);
      setPlannerSummary(null);
      setError(null);
    } catch (resetError) {
      console.error('Error clearing assignments:', resetError);
      setError(translations.coordinator.resetPlanFailed);
    }
  };

  const handleRefreshAssignments = async () => {
    try {
      const response = await shiftService.getCurrentAssignments();
      setPlannerSummary(response.data.planner || null);

      if (response.data.assignments && response.data.assignments.length > 0) {
        setCurrentAssignments(response.data.assignments);
      } else {
        setCurrentAssignments(null);
      }
    } catch (refreshError) {
      console.log('Error refreshing assignments:', refreshError.message);
      setCurrentAssignments(null);
    }
  };

  const assignmentStats = useMemo(() => {
    const userShiftCounts = new Map();
    const groupShiftCounts = new Map();

    (users || []).forEach((user) => {
      userShiftCounts.set(user.id, 0);
    });

    (currentAssignments || []).forEach((assignment) => {
      userShiftCounts.set(
        assignment.user_id,
        (userShiftCounts.get(assignment.user_id) || 0) + 1
      );

      if (assignment.assigned_via === 'group' && assignment.group_name) {
        if (!groupShiftCounts.has(assignment.group_name)) {
          groupShiftCounts.set(assignment.group_name, new Set());
        }

        groupShiftCounts.get(assignment.group_name).add(assignment.shift_id);
      }
    });

    return {
      userShiftCounts,
      groupShiftCounts,
    };
  }, [currentAssignments, users]);

  const selectionOptions = useMemo(() => {
    const userOptions = [...(users || [])]
      .filter((user) => !user.group_id)
      .sort((a, b) => a.username.localeCompare(b.username, 'de'))
      .map((user) => ({
        key: `user-${user.id}`,
        id: user.id,
        type: 'user',
        label: user.username,
        shiftCount: assignmentStats.userShiftCounts.get(user.id) || 0,
      }));

    const teamOptions = [...groupOptions]
      .sort((a, b) => a.name.localeCompare(b.name, 'de'))
      .map((group) => ({
        key: `group-${group.id}`,
        id: group.id,
        type: 'group',
        label: group.name,
        name: group.name,
        shiftCount: assignmentStats.groupShiftCounts.get(group.name)?.size || 0,
      }));

    return [...userOptions, ...teamOptions];
  }, [assignmentStats.groupShiftCounts, assignmentStats.userShiftCounts, groupOptions, users]);

  const teamColorMap = useMemo(() => {
    return buildTeamColorMap(teamDirectory);
  }, [teamDirectory]);

  const selectedViewOption = useMemo(() => {
    return selectionOptions.find((option) => option.key === selectedViewKey) || null;
  }, [selectedViewKey, selectionOptions]);

  useEffect(() => {
    if (viewMode !== 'person' || selectionOptions.length === 0) {
      return;
    }

    const selectedOptionStillExists = selectionOptions.some(
      (option) => option.key === selectedViewKey
    );

    if (!selectedViewKey || !selectedOptionStillExists) {
      const firstAssignedUser = selectionOptions.find(
        (option) => option.type === 'user' && option.shiftCount > 0
      );
      const firstAssignedTeam = selectionOptions.find(
        (option) => option.type === 'group' && option.shiftCount > 0
      );

      setSelectedViewKey((firstAssignedUser || firstAssignedTeam || selectionOptions[0]).key);
    }
  }, [selectedViewKey, selectionOptions, viewMode]);

  return (
    <Box sx={{ pt: { xs: 0.5, md: 1 }, px: 0, pb: 0 }}>
      <ActionBar sx={{ mb: 2 }}>
        <Stack
          direction={{ xs: 'column', lg: 'row' }}
          spacing={1}
          sx={{ flexWrap: 'wrap', alignItems: { lg: 'center' } }}
        >
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Button
              variant="contained"
              size="small"
              startIcon={isGenerating ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
              onClick={handleGeneratePlan}
              disabled={isGenerating}
              sx={{ whiteSpace: 'nowrap' }}
            >
              {isGenerating ? translations.coordinator.generating : translations.coordinator.generatePlan}
            </Button>
            <Button
              variant="outlined"
              color="error"
              size="small"
              startIcon={<DeleteSweepIcon />}
              onClick={handleResetAllAssignments}
              disabled={isGenerating || !currentAssignments}
              sx={{ whiteSpace: 'nowrap' }}
            >
              {translations.coordinator.resetPlan}
            </Button>
          </Stack>

          <TextField
            type="number"
            label={translations.coordinator.maxShiftsPerUser}
            value={maxShiftsPerUser}
            onChange={(event) => setMaxShiftsPerUser(parseInt(event.target.value, 10) || 10)}
            inputProps={{ min: 1, max: 20 }}
            sx={{ width: { xs: '100%', sm: 220 } }}
            size="small"
          />
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ ml: { lg: 'auto' }, whiteSpace: 'nowrap' }}
          >
            {`${translations.coordinator.registeredPeople}: ${registeredPeopleCount}`}
          </Typography>
        </Stack>
      </ActionBar>

      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          {translations.coordinator.viewModeLabel}
        </Typography>
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={1.5}
          sx={{ alignItems: { md: 'center' } }}
        >
          <ToggleButtonGroup
            exclusive
            value={viewMode}
            onChange={(_, nextView) => {
              if (nextView) {
                setViewMode(nextView);
              }
            }}
            color="primary"
            sx={{ flexWrap: 'wrap' }}
          >
            <ToggleButton value="day">
              {translations.coordinator.dayPlanView}
            </ToggleButton>
            <ToggleButton value="person">
              {translations.coordinator.personView}
            </ToggleButton>
          </ToggleButtonGroup>

          {viewMode === 'person' && (
            <Autocomplete
              disableClearable
              size="small"
              options={selectionOptions}
              value={selectedViewOption}
              loading={loadingSelectionContext}
              onChange={(_, nextValue) => setSelectedViewKey(nextValue?.key || '')}
              getOptionLabel={formatSelectionLabel}
              isOptionEqualToValue={(option, value) => option.key === value.key}
              groupBy={(option) => (
                option.type === 'group'
                  ? translations.coordinator.teamsLabel
                  : translations.coordinator.peopleLabel
              )}
              noOptionsText={loadingSelectionContext
                ? translations.coordinator.loadingPeople
                : translations.coordinator.noMatchingPeople}
              sx={{ minWidth: { xs: '100%', md: 320 } }}
              renderOption={(props, option) => {
                const { key, ...optionProps } = props;
                const teamColor = option.type === 'group' ? getTeamColor(option.label, teamColorMap) : null;

                return (
                  <Box component="li" key={key} {...optionProps}>
                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center', width: '100%' }}>
                      {teamColor && (
                        <Box
                          sx={{
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            flexShrink: 0,
                            backgroundColor: teamColor.accent,
                            border: `1px solid ${teamColor.accent}`,
                            boxShadow: `0 0 0 2px ${teamColor.surface}`,
                          }}
                        />
                      )}
                      <Typography variant="body2">{formatSelectionLabel(option)}</Typography>
                    </Stack>
                  </Box>
                );
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label={translations.coordinator.choosePersonOrGroup}
                />
              )}
            />
          )}
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {viewMode === 'day' ? (
        <CoordinatorShiftGrid
          shifts={shifts}
          generatedAssignments={currentAssignments}
          maxShiftsPerUser={maxShiftsPerUser}
          teamColorMap={teamColorMap}
          onAssignmentsChange={handleRefreshAssignments}
        />
      ) : (
        <CoordinatorPersonView
          shifts={shifts}
          selectedViewOption={selectedViewOption}
          generatedAssignments={currentAssignments}
          userOptOuts={userOptOuts}
          groupOptOuts={groupOptOuts}
          loadingSelectionContext={loadingSelectionContext || !selectionContextLoaded}
        />
      )}
    </Box>
  );
};

export default CoordinatorView;
