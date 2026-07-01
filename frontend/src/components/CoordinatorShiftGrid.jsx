import React, { useEffect, useMemo, useState } from 'react';
import {
  Avatar,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  GlobalStyles,
  InputAdornment,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography
} from '@mui/material';
import { alpha, styled } from '@mui/material/styles';
import PersonIcon from '@mui/icons-material/Person';
import GroupIcon from '@mui/icons-material/Group';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import PrintIcon from '@mui/icons-material/Print';
import DownloadIcon from '@mui/icons-material/Download';
import { groupService, shiftService } from '../services/api';
import { getTeamColor } from '../utils/teamColors';
import { translations } from '../utils/translations';

const LOCATION_META = {
  weinzelt: {
    key: 'weinzelt',
    label: 'Weinzelt',
    accent: '#d65f8f',
    surface: '#fde8f1'
  },
  bierwagen: {
    key: 'bierwagen',
    label: 'Bierwagen',
    accent: '#1f9ac0',
    surface: '#e5f7fd'
  },
  other: {
    key: 'other',
    label: 'Sonstiges',
    accent: '#6f6f6f',
    surface: '#f3f4f6'
  }
};

const PlannerHeaderCell = styled(Box)(({ theme }) => ({
  padding: theme.spacing(1.5, 2),
  borderBottom: `1px solid ${theme.palette.divider}`,
  borderRight: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.grey[100],
  fontWeight: 700,
  '@media print': {
    padding: theme.spacing(1.1, 1.5),
    borderColor: '#000000',
    backgroundColor: '#f2f2f2',
    color: '#000000',
    WebkitPrintColorAdjust: 'exact',
    printColorAdjust: 'exact',
  },
}));

const LocationHeaderCell = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'accentColor' && prop !== 'surfaceColor',
})(({ accentColor, surfaceColor, theme }) => ({
  padding: theme.spacing(1.5, 2),
  borderBottom: `1px solid ${theme.palette.divider}`,
  borderRight: `1px solid ${theme.palette.divider}`,
  backgroundColor: surfaceColor,
  color: accentColor,
  fontWeight: 700,
  '@media print': {
    padding: theme.spacing(1.1, 1.5),
    borderColor: '#000000',
    color: '#000000',
    WebkitPrintColorAdjust: 'exact',
    printColorAdjust: 'exact',
  },
}));

const TimeCell = styled(Box)(({ theme }) => ({
  padding: theme.spacing(1.5, 2),
  borderBottom: `1px solid ${theme.palette.divider}`,
  borderRight: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.grey[50],
  minHeight: 124,
  '@media print': {
    padding: theme.spacing(1, 1.4),
    minHeight: 100,
    borderColor: '#000000',
    backgroundColor: '#fafafa',
    color: '#000000',
    WebkitPrintColorAdjust: 'exact',
    printColorAdjust: 'exact',
  },
}));

const ShiftCell = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'staffingLevel' && prop !== 'accentColor',
})(({ staffingLevel, accentColor, theme }) => {
  const paletteByLevel = {
    empty: theme.palette.grey[100],
    understaffed: alpha(theme.palette.error.main, 0.08),
    partial: alpha(theme.palette.warning.main, 0.12),
    full: alpha(theme.palette.success.main, 0.1),
    overstaffed: alpha(theme.palette.info.main, 0.12),
    none: theme.palette.grey[50]
  };

  return {
    padding: theme.spacing(1.25),
    borderBottom: `1px solid ${theme.palette.divider}`,
    borderRight: `1px solid ${theme.palette.divider}`,
    backgroundColor: paletteByLevel[staffingLevel] || theme.palette.background.paper,
    minHeight: 124,
    position: 'relative',
    '&::before': {
      content: '""',
      position: 'absolute',
      top: 0,
      left: 0,
      bottom: 0,
      width: 4,
      backgroundColor: accentColor,
    },
    '@media print': {
      minHeight: 100,
      padding: theme.spacing(0.9, 1),
      borderColor: '#000000',
      backgroundColor: '#ffffff',
      color: '#000000',
      WebkitPrintColorAdjust: 'exact',
      printColorAdjust: 'exact',
      '&::before': {
        width: 0,
      },
    },
  };
});

const CompactAssignmentsGrid = styled(Box)(({ theme }) => ({
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
  gap: theme.spacing(0.75),
  '@media print': {
    gap: theme.spacing(0.5),
  },
}));

const CompactNameTag = styled(Box, {
  shouldForwardProp: (prop) => !['assignmentTone', 'teamAccentColor', 'teamSurfaceColor'].includes(prop),
})(({ assignmentTone, teamAccentColor, teamSurfaceColor, theme }) => ({
  display: 'flex',
  alignItems: 'center',
  minWidth: 0,
  minHeight: 30,
  padding: theme.spacing(0.5, 0.75),
  borderRadius: theme.spacing(1),
  border: `1px solid ${assignmentTone === 'group'
    ? teamAccentColor || alpha(theme.palette.secondary.main, 0.3)
    : theme.palette.divider}`,
  backgroundColor: assignmentTone === 'group'
    ? teamSurfaceColor || alpha(theme.palette.secondary.main, 0.12)
    : theme.palette.background.paper,
  overflow: 'hidden',
  position: 'relative',
  color: theme.palette.text.primary,
  '&::before': assignmentTone === 'group' ? {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    width: 4,
    backgroundColor: teamAccentColor || theme.palette.secondary.main,
  } : undefined,
  '@media print': {
    minHeight: 24,
    padding: theme.spacing(0.35, 0.55),
    borderColor: '#000000',
    backgroundColor: '#ffffff',
    color: '#000000',
    WebkitPrintColorAdjust: 'exact',
    printColorAdjust: 'exact',
  },
}));

const DialogAssignmentRow = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: theme.spacing(1),
  padding: theme.spacing(0.75, 1),
  borderRadius: theme.spacing(1),
  border: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.background.paper,
}));

const formatTime = (dateTimeStr) => {
  const date = new Date(dateTimeStr);
  return date.toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
};

const getPlannerDayDate = (dateTimeStr) => {
  const date = new Date(dateTimeStr);

  // Treat after-midnight shifts as part of the previous festival night.
  if (date.getHours() < 6) {
    date.setDate(date.getDate() - 1);
  }

  return date;
};

const formatDayTabLabel = (dateValue) => {
  const date = new Date(dateValue);
  return date.toLocaleDateString('de-DE', {
    weekday: 'short',
    day: 'numeric',
    month: 'short'
  });
};

const formatPrintDayLabel = (dateValue) => {
  const date = new Date(dateValue);
  return date.toLocaleDateString('de-DE', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });
};

const formatPrintTimestamp = (date) => {
  if (!date) {
    return '';
  }

  return date.toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
};

const getSortMinutes = (dateTime) => {
  const time = new Date(dateTime);
  const hours = time.getHours();
  const minutes = time.getMinutes();

  return (hours < 6 ? hours + 24 : hours) * 60 + minutes;
};

const getLocationInfo = (title) => {
  const normalizedTitle = title.toLowerCase();

  if (normalizedTitle.includes('wein')) {
    return LOCATION_META.weinzelt;
  }

  if (normalizedTitle.includes('bier')) {
    return LOCATION_META.bierwagen;
  }

  return {
    ...LOCATION_META.other,
    label: title
  };
};

const getCurrentStaff = (shift) => {
  return (shift.users?.length || 0)
    + (shift.groups?.reduce((sum, group) => sum + group.users.length, 0) || 0);
};

const getStaffingLevel = (shift) => {
  const currentStaff = getCurrentStaff(shift);
  const capacity = shift.capacity;

  if (currentStaff === 0) {
    return 'empty';
  }

  if (!capacity) {
    return 'partial';
  }

  if (currentStaff < capacity) {
    return capacity - currentStaff === 1 ? 'partial' : 'understaffed';
  }

  if (currentStaff === capacity) {
    return 'full';
  }

  return 'overstaffed';
};

const getStatusLabel = (shift) => {
  const currentStaff = getCurrentStaff(shift);
  const capacity = shift.capacity;

  if (!capacity) {
    return `${currentStaff} eingeteilt`;
  }

  if (currentStaff === 0) {
    return translations.grid.empty;
  }

  if (currentStaff < capacity) {
    const missingStaff = capacity - currentStaff;
    return missingStaff === 1 ? '1 Person fehlt' : `${missingStaff} Personen fehlen`;
  }

  if (currentStaff === capacity) {
    return translations.grid.fullyStaffed;
  }

  const extraStaff = currentStaff - capacity;
  return extraStaff === 1 ? '1 Person mehr als geplant' : `${extraStaff} Personen mehr als geplant`;
};

const getStatusColor = (level) => {
  switch (level) {
    case 'understaffed':
      return 'error';
    case 'partial':
      return 'warning';
    case 'full':
      return 'success';
    case 'overstaffed':
      return 'info';
    default:
      return 'default';
  }
};

const getDayIssueCount = (dayPlan, locationColumns) => {
  return dayPlan.slots.reduce((sum, slot) => {
    return sum + locationColumns.reduce((slotSum, location) => {
      const shift = slot.locations[location.key];

      if (!shift || !shift.capacity) {
        return slotSum;
      }

      return slotSum + (getCurrentStaff(shift) < shift.capacity ? 1 : 0);
    }, 0);
  }, 0);
};

const getShiftPreviewEntries = (shift) => {
  const groupEntries = (shift.groups || []).flatMap((group) =>
    group.users.map((user) => ({
      key: `group-${group.name}-${user.id}`,
      label: user.username,
      assignmentTone: 'group',
      groupName: group.name,
      helper: group.name,
    }))
  );

  const userEntries = (shift.users || []).map((user) => ({
    key: `user-${user.id}`,
    label: user.username,
    assignmentTone: 'individual',
    helper: translations.grid.directAssignment,
  }));

  return [...groupEntries, ...userEntries];
};

const getPrintEntryColumns = (entries) => {
  const columns = [[], [], []];

  entries.slice(0, 6).forEach((entry, index) => {
    const columnIndex = index % 3;
    columns[columnIndex].push(entry);
  });

  return columns.map((columnEntries) => {
    if (columnEntries.length === 0) {
      return [null, null];
    }

    if (columnEntries.length === 1) {
      return [columnEntries[0], null];
    }

    return columnEntries.slice(0, 2);
  });
};

const PRINT_SHIFT_DIVIDER = '1.8px solid #000000';

const CoordinatorShiftGrid = ({
  shifts,
  generatedAssignments,
  maxShiftsPerUser,
  teamColorMap,
  onAssignmentsChange,
}) => {
  const [addUserDialogOpen, setAddUserDialogOpen] = useState(false);
  const [selectedShift, setSelectedShift] = useState(null);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [availableGroups, setAvailableGroups] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedDayKey, setSelectedDayKey] = useState('');
  const [printTimestamp, setPrintTimestamp] = useState(null);

  const shiftsWithAssignments = useMemo(() => {
    if (!generatedAssignments) {
      return shifts.map((shift) => ({
        ...shift,
        users: [],
        groups: [],
      }));
    }

    return shifts.map((shift) => {
      const shiftAssignments = generatedAssignments.filter(
        (assignment) => assignment.shift_id === shift.id
      );
      const userAssignments = shiftAssignments.filter((assignment) => assignment.assigned_via === 'individual');
      const groupAssignments = shiftAssignments.filter((assignment) => assignment.assigned_via === 'group');
      const uniqueGroups = {};

      groupAssignments.forEach((assignment) => {
        if (!uniqueGroups[assignment.group_name]) {
          uniqueGroups[assignment.group_name] = {
            name: assignment.group_name,
            users: [],
          };
        }

        uniqueGroups[assignment.group_name].users.push({
          id: assignment.user_id,
          username: assignment.username
        });
      });

      return {
        ...shift,
        users: userAssignments.map((assignment) => ({
          id: assignment.user_id,
          username: assignment.username,
          assignedVia: 'individual',
        })),
        groups: Object.values(uniqueGroups),
      };
    });
  }, [generatedAssignments, shifts]);

  const assignmentCountByUserId = useMemo(() => {
    const counts = new Map();

    (generatedAssignments || []).forEach((assignment) => {
      counts.set(assignment.user_id, (counts.get(assignment.user_id) || 0) + 1);
    });

    return counts;
  }, [generatedAssignments]);

  const { dayPlans, locationColumns } = useMemo(() => {
    const grouped = {};
    const locationMap = {};

    shiftsWithAssignments.forEach((shift) => {
      const locationInfo = getLocationInfo(shift.title);
      const plannerDayDate = getPlannerDayDate(shift.start_time);
      const dayKey = plannerDayDate.toDateString();
      const timeLabel = `${formatTime(shift.start_time)} - ${formatTime(shift.end_time)}`;

      locationMap[locationInfo.key] = locationInfo;

      if (!grouped[dayKey]) {
        grouped[dayKey] = {
          dayKey,
          dayDate: plannerDayDate.toISOString(),
          slots: {}
        };
      }

      if (!grouped[dayKey].slots[timeLabel]) {
        grouped[dayKey].slots[timeLabel] = {
          key: `${dayKey}-${timeLabel}`,
          timeLabel,
          sortValue: getSortMinutes(shift.start_time),
          locations: {}
        };
      }

      grouped[dayKey].slots[timeLabel].locations[locationInfo.key] = {
        ...shift,
        locationInfo
      };
    });

    const orderedLocationKeys = Object.keys(locationMap).sort((a, b) => {
      const preferredOrder = ['weinzelt', 'bierwagen'];
      const aIndex = preferredOrder.indexOf(a);
      const bIndex = preferredOrder.indexOf(b);

      if (aIndex !== -1 || bIndex !== -1) {
        if (aIndex === -1) {
          return 1;
        }

        if (bIndex === -1) {
          return -1;
        }

        return aIndex - bIndex;
      }

      return locationMap[a].label.localeCompare(locationMap[b].label, 'de');
    });

    return {
      dayPlans: Object.values(grouped)
        .sort((a, b) => new Date(a.dayDate) - new Date(b.dayDate))
        .map((dayPlan) => ({
          ...dayPlan,
          slots: Object.values(dayPlan.slots).sort((a, b) => a.sortValue - b.sortValue)
        })),
      locationColumns: orderedLocationKeys.map((key) => locationMap[key])
    };
  }, [shiftsWithAssignments]);

  const defaultDayKey = useMemo(() => {
    const firstDayWithIssues = dayPlans.find(
      (dayPlan) => getDayIssueCount(dayPlan, locationColumns) > 0
    );

    return firstDayWithIssues?.dayKey || dayPlans[0]?.dayKey || '';
  }, [dayPlans, locationColumns]);

  useEffect(() => {
    if (!dayPlans.length) {
      return;
    }

    const selectedDayStillExists = dayPlans.some((dayPlan) => dayPlan.dayKey === selectedDayKey);

    if (!selectedDayKey || !selectedDayStillExists) {
      setSelectedDayKey(defaultDayKey);
    }
  }, [dayPlans, defaultDayKey, selectedDayKey]);

  const resolvedDayKey = selectedDayKey || defaultDayKey;

  const activeDayPlan = useMemo(() => {
    return dayPlans.find((dayPlan) => dayPlan.dayKey === resolvedDayKey) || dayPlans[0];
  }, [dayPlans, resolvedDayKey]);

  const handlePrintActiveDay = () => {
    if (typeof window === 'undefined' || !activeDayPlan) {
      return;
    }

    setPrintTimestamp(new Date());

    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        window.print();
      });
    });
  };

  const handleExportXlsx = async () => {
    if (typeof window === 'undefined' || dayPlans.length === 0) {
      return;
    }

    try {
      const response = await shiftService.exportPlanXlsx(generatedAssignments || null);
      const downloadUrl = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = 'open-flair-schichtplan.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (exportError) {
      console.error('Error exporting XLSX plan:', exportError);
    }
  };

  const handleOpenAddUserDialog = async (shift) => {
    setSelectedShift(shift);
    setLoading(true);
    setAddUserDialogOpen(true);

    try {
      const usersResponse = await shiftService.getAvailableUsers(shift.id);
      const allUsers = usersResponse.data;
      const groupsResponse = await groupService.getGroups();
      const allGroups = groupsResponse.data;
      const individualUsers = allUsers.filter((user) => !user.group_id);
      const assignedGroupNames = shift.groups?.map((group) => group.name) || [];
      const availableGroupsBasic = allGroups.filter(
        (group) => !assignedGroupNames.includes(group.name) && group.is_active
      );

      const availableGroupsWithUsers = await Promise.all(
        availableGroupsBasic.map(async (group) => {
          try {
            const groupDetailResponse = await groupService.getGroup(group.id);
            return groupDetailResponse.data;
          } catch (loadError) {
            console.error(`Error fetching details for group ${group.id}:`, loadError);
            return { ...group, users: [] };
          }
        })
      );

      setAvailableUsers(
        individualUsers.filter(
          (user) => (assignmentCountByUserId.get(user.id) || 0) < maxShiftsPerUser
        )
      );
      setAvailableGroups(
        availableGroupsWithUsers.filter((group) => group.users && group.users.length > 0)
          .filter((group) => group.users.every((user) => !user.is_coordinator))
          .filter((group) => group.users.every(
            (user) => (assignmentCountByUserId.get(user.id) || 0) < maxShiftsPerUser
          ))
      );
    } catch (loadError) {
      console.error('Error loading available users/groups:', loadError);
    } finally {
      setLoading(false);
    }
  };

  const handleAddUser = async (userId) => {
    try {
      await shiftService.addUserToShift({
        shift_id: selectedShift.id,
        user_id: userId
      });

      if (onAssignmentsChange) {
        await onAssignmentsChange();
      }

      setAddUserDialogOpen(false);
      setSelectedShift(null);
      setSearchTerm('');
    } catch (addError) {
      console.error('Error adding user to shift:', addError);
    }
  };

  const handleAddGroup = async (groupId) => {
    try {
      await shiftService.addGroupToShift({
        shift_id: selectedShift.id,
        group_id: groupId
      });

      if (onAssignmentsChange) {
        await onAssignmentsChange();
      }

      setAddUserDialogOpen(false);
      setSelectedShift(null);
      setSearchTerm('');
    } catch (addError) {
      console.error('Error adding group to shift:', addError);
    }
  };

  const handleRemoveUser = async (shift, userId) => {
    try {
      await shiftService.removeUserFromShift(shift.id, userId);

      if (onAssignmentsChange) {
        await onAssignmentsChange();
      }

      setAddUserDialogOpen(false);
      setSelectedShift(null);
    } catch (removeError) {
      console.error('Error removing user from shift:', removeError);
    }
  };

  const handleRemoveGroup = async (shift, groupName) => {
    try {
      const groupsResponse = await groupService.getGroups();
      const group = groupsResponse.data.find((entry) => entry.name === groupName);

      if (!group) {
        return;
      }

      await shiftService.removeGroupFromShift(shift.id, group.id);

      if (onAssignmentsChange) {
        await onAssignmentsChange();
      }

      setAddUserDialogOpen(false);
      setSelectedShift(null);
    } catch (removeError) {
      console.error('Error removing group from shift:', removeError);
    }
  };

  const filteredUsers = availableUsers.filter((user) =>
    user.username.toLowerCase().includes(searchTerm.toLowerCase())
    || user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredGroups = availableGroups.filter((group) =>
    group.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (shiftsWithAssignments.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          {translations.grid.noShiftsAvailable}
        </Typography>
      </Paper>
    );
  }

  const activePrintTimestamp = printTimestamp || new Date();

  const screenPlanGrid = activeDayPlan ? (
    <Box sx={{ overflowX: 'auto', '@media print': { overflow: 'visible' } }}>
      <Box
        sx={{
          minWidth: Math.max(840, 180 + locationColumns.length * 320),
          display: 'grid',
          gridTemplateColumns: `180px repeat(${locationColumns.length}, minmax(320px, 1fr))`,
          '@media print': {
            minWidth: 0,
            width: '100%',
            gridTemplateColumns: `160px repeat(${locationColumns.length}, minmax(0, 1fr))`,
          },
        }}
      >
        <PlannerHeaderCell>
          <Typography variant="subtitle2">{translations.grid.time}</Typography>
        </PlannerHeaderCell>
        {locationColumns.map((location) => (
          <LocationHeaderCell
            key={location.key}
            accentColor={location.accent}
            surfaceColor={location.surface}
          >
            <Typography variant="subtitle2">{location.label}</Typography>
          </LocationHeaderCell>
        ))}

        {activeDayPlan.slots.map((slot) => (
          <React.Fragment key={slot.key}>
            <TimeCell>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, '@media print': { fontSize: '0.95rem' } }}>
                {slot.timeLabel}
              </Typography>
            </TimeCell>

            {locationColumns.map((location) => {
              const shift = slot.locations[location.key];

              if (!shift) {
                return (
                  <ShiftCell
                    key={`${slot.key}-${location.key}`}
                    staffingLevel="none"
                    accentColor={location.accent}
                  >
                    <Typography variant="body2" color="text.secondary">
                      {translations.grid.noShiftHere}
                    </Typography>
                  </ShiftCell>
                );
              }

              const staffingLevel = getStaffingLevel(shift);
              const currentStaff = getCurrentStaff(shift);

              return (
                <ShiftCell
                  key={shift.id}
                  staffingLevel={staffingLevel}
                  accentColor={location.accent}
                >
                  <Stack spacing={1} sx={{ '@media print': { gap: 0.6 } }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
                        {currentStaff}/{shift.capacity || '∞'} {translations.shifts.capacity.toLowerCase()}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                        <Chip
                          size="small"
                          color={getStatusColor(staffingLevel)}
                          label={getStatusLabel(shift)}
                          sx={{
                            height: 24,
                            '@media print': {
                              height: 20,
                              fontSize: '0.72rem',
                              border: '1px solid #000000',
                              backgroundColor: '#ffffff',
                              color: '#000000',
                            },
                          }}
                        />
                        <Tooltip title={translations.grid.editShift}>
                          <IconButton
                            className="coordinator-print-hidden"
                            size="small"
                            color="primary"
                            onClick={() => handleOpenAddUserDialog(shift)}
                            aria-label={translations.grid.editShift}
                          >
                            <AddIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>

                    {currentStaff > 0 ? (
                      <CompactAssignmentsGrid>
                        {getShiftPreviewEntries(shift).map((entry) => {
                          const teamColor = entry.groupName ? getTeamColor(entry.groupName, teamColorMap) : null;

                          return (
                          <Tooltip
                            key={entry.key}
                            title={entry.helper}
                            enterDelay={300}
                          >
                            <CompactNameTag
                              assignmentTone={entry.assignmentTone}
                              teamAccentColor={teamColor?.border}
                              teamSurfaceColor={teamColor?.surface}
                            >
                              <Typography
                                variant="body2"
                                sx={{
                                  fontSize: '0.82rem',
                                  lineHeight: 1.2,
                                  whiteSpace: 'nowrap',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  fontWeight: 500,
                                  '@media print': {
                                    fontSize: '0.74rem',
                                  },
                                }}
                              >
                                {entry.label}
                              </Typography>
                            </CompactNameTag>
                          </Tooltip>
                          );
                        })}
                      </CompactAssignmentsGrid>
                    ) : (
                      <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                        {translations.grid.noAssignments}
                      </Typography>
                    )}
                  </Stack>
                </ShiftCell>
              );
            })}
          </React.Fragment>
        ))}
      </Box>
    </Box>
  ) : null;

  const printPlanGrid = activeDayPlan ? (
    <Box
      className="coordinator-print-only"
      sx={{
        display: 'none',
        '@media print': {
          display: 'block',
        },
      }}
    >
      <Box sx={{ mb: 1.25 }}>
        <Typography
          variant="subtitle1"
          sx={{
            color: '#000000',
            fontWeight: 700,
            fontSize: '0.98rem',
            lineHeight: 1.2,
          }}
        >
          {formatPrintDayLabel(activeDayPlan.dayDate)} • {translations.grid.printTimestampLabel}: {formatPrintTimestamp(activePrintTimestamp)}
        </Typography>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: `repeat(${locationColumns.length}, minmax(0, 1fr))`,
          gap: '2.5mm',
        }}
      >
        {locationColumns.map((location) => (
          <Box
            key={`print-${location.key}`}
            sx={{
              border: '1px solid #000000',
              color: '#000000',
              backgroundColor: '#ffffff',
              breakInside: 'avoid',
            }}
          >
            <Box
              sx={{
                px: 1,
                py: 0.7,
                borderBottom: '1px solid #000000',
                backgroundColor: location.surface,
                color: '#000000',
                textAlign: 'center',
                fontWeight: 700,
                fontSize: '0.9rem',
                lineHeight: 1.15,
                WebkitPrintColorAdjust: 'exact',
                printColorAdjust: 'exact',
              }}
            >
              {location.label}
            </Box>

            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: '20mm repeat(3, minmax(0, 1fr)) 10mm',
                borderBottom: '1px solid #000000',
                backgroundColor: '#f7f7f7',
                color: '#000000',
                fontSize: '0.72rem',
                fontWeight: 700,
                lineHeight: 1.15,
                WebkitPrintColorAdjust: 'exact',
                printColorAdjust: 'exact',
              }}
            >
              <Box sx={{ px: 0.7, py: 0.45, borderRight: '1px solid #000000' }}>
                {translations.grid.time}
              </Box>
              <Box sx={{ px: 0.7, py: 0.45, gridColumn: 'span 3', borderRight: '1px solid #000000' }}>
                {translations.grid.namesColumn}
              </Box>
              <Box sx={{ px: 0.5, py: 0.45, textAlign: 'center' }}>
                {translations.grid.peopleShort}
              </Box>
            </Box>

            {activeDayPlan.slots.map((slot) => {
              const shift = slot.locations[location.key];
              const printColumns = getPrintEntryColumns(shift ? getShiftPreviewEntries(shift) : []);

              return (
                <Box
                  key={`print-row-${location.key}-${slot.key}`}
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: '20mm repeat(3, minmax(0, 1fr)) 10mm',
                    borderBottom: PRINT_SHIFT_DIVIDER,
                    '&:last-of-type': {
                      borderBottom: 'none',
                    },
                  }}
                >
                  <Box
                    sx={{
                      px: 0.7,
                      py: 0.55,
                      borderRight: '1px solid #000000',
                      minHeight: '19mm',
                      fontSize: '0.76rem',
                      fontWeight: 700,
                      lineHeight: 1.15,
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    {slot.timeLabel}
                  </Box>

                  {printColumns.map((columnEntries, columnIndex) => (
                    <Box
                      key={`print-col-${location.key}-${slot.key}-${columnIndex}`}
                      sx={{
                        borderRight: '1px solid #000000',
                        minHeight: '19mm',
                        display: 'grid',
                        gridTemplateRows: 'repeat(2, minmax(0, 1fr))',
                        overflow: 'hidden',
                      }}
                    >
                      {columnEntries.map((entry, rowIndex) => (
                        <Box
                          key={entry ? entry.key : `empty-${location.key}-${slot.key}-${columnIndex}-${rowIndex}`}
                          sx={{
                            px: 0.55,
                            py: 0.35,
                            borderBottom: rowIndex === 0 ? '1px solid #000000' : 'none',
                            minHeight: '9.5mm',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              fontSize: '0.72rem',
                              lineHeight: 1.08,
                              fontWeight: 500,
                              color: '#000000',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              width: '100%',
                            }}
                          >
                            {entry?.label || ''}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  ))}

                  <Box
                    sx={{
                      px: 0.35,
                      py: 0.35,
                      minHeight: '19mm',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      color: '#000000',
                    }}
                  >
                    {shift?.capacity || ''}
                  </Box>
                </Box>
              );
            })}
          </Box>
        ))}
      </Box>
    </Box>
  ) : null;

  return (
    <Box>
      <GlobalStyles
        styles={{
          '@page': {
            size: 'A4 landscape',
            margin: '6mm',
          },
          '@media print': {
            'html, body': {
              backgroundColor: '#ffffff',
            },
            'body *': {
              visibility: 'hidden',
            },
            '.coordinator-print-shell, .coordinator-print-shell *': {
              visibility: 'visible',
            },
            '.coordinator-print-shell': {
              position: 'absolute',
              left: 0,
              top: 0,
              width: '100%',
              backgroundColor: '#ffffff',
            },
            '.coordinator-print-hidden': {
              display: 'none !important',
            },
            '.coordinator-screen-plan': {
              display: 'none !important',
            },
            '.coordinator-print-only': {
              display: 'block !important',
            },
          },
        }}
      />
      <Paper sx={{ mb: 2, borderRadius: 2.5, overflow: 'hidden' }}>
        <Box
          className="coordinator-print-hidden"
          sx={{
            px: 1.5,
            py: 1.5,
            borderBottom: 1,
            borderColor: 'divider',
            backgroundColor: 'grey.50',
          }}
        >
          <Stack
            direction={{ xs: 'column', lg: 'row' }}
            spacing={1.5}
            sx={{ alignItems: { lg: 'center' }, justifyContent: 'space-between' }}
          >
            <ToggleButtonGroup
              exclusive
              value={resolvedDayKey || null}
              onChange={(_, value) => {
                if (value) {
                  setSelectedDayKey(value);
                }
              }}
              sx={(theme) => ({
                display: 'flex',
                flexWrap: 'wrap',
                gap: 1,
                '& .MuiToggleButtonGroup-grouped': {
                  margin: 0,
                  borderRadius: theme.spacing(1.5),
                  border: `1px solid ${theme.palette.divider} !important`,
                },
              })}
            >
              {dayPlans.map((dayPlan) => {
                const issueCount = getDayIssueCount(dayPlan, locationColumns);

                return (
                  <ToggleButton
                    key={dayPlan.dayKey}
                    value={dayPlan.dayKey}
                    sx={{
                      alignItems: 'flex-start',
                      textAlign: 'left',
                      textTransform: 'none',
                      px: 1.5,
                      py: 0.9,
                      minWidth: 136,
                    }}
                  >
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
                        {formatDayTabLabel(dayPlan.dayDate)}
                      </Typography>
                      <Typography
                        variant="caption"
                        color={issueCount > 0 ? 'error.main' : 'text.secondary'}
                        sx={{ whiteSpace: 'nowrap', fontWeight: issueCount > 0 ? 700 : 500 }}
                      >
                        {issueCount > 0 ? `${issueCount} offen` : translations.grid.everythingCovered}
                      </Typography>
                    </Box>
                  </ToggleButton>
                );
              })}
            </ToggleButtonGroup>

            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1}
              sx={{ alignSelf: { xs: 'stretch', lg: 'center' } }}
            >
              <Button
                variant="outlined"
                size="small"
                startIcon={<DownloadIcon />}
              onClick={handleExportXlsx}
                disabled={!dayPlans.length}
                sx={{ whiteSpace: 'nowrap' }}
              >
                {translations.grid.exportXlsx}
              </Button>
              <Button
                variant="outlined"
                size="small"
                startIcon={<PrintIcon />}
                onClick={handlePrintActiveDay}
                disabled={!activeDayPlan}
                sx={{ whiteSpace: 'nowrap' }}
              >
                {translations.grid.printActiveDay}
              </Button>
            </Stack>
          </Stack>
        </Box>

        {activeDayPlan && (
          <Box className="coordinator-print-shell">
            <Box className="coordinator-screen-plan">
              {screenPlanGrid}
            </Box>
            {printPlanGrid}
          </Box>
        )}
      </Paper>

      <Dialog
        open={addUserDialogOpen}
        onClose={() => setAddUserDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle component="div">
          <Typography variant="h6" component="div">
            {translations.grid.editDialogTitle}
          </Typography>
          {selectedShift && (
            <Typography variant="body2" component="div" color="text.secondary">
              {`${selectedShift.title} • ${formatTime(selectedShift.start_time)}-${formatTime(selectedShift.end_time)}`}
            </Typography>
          )}
        </DialogTitle>

        <DialogContent>
          {selectedShift && (
            <Box sx={{ mb: 2.5 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                {translations.grid.currentAssignments}
              </Typography>

              <Stack spacing={1}>
                {selectedShift.groups?.map((group) => (
                  <DialogAssignmentRow key={`dialog-group-${group.name}`}>
                    <Box sx={{ minWidth: 0 }}>
                      <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', mb: 0.25 }}>
                        <Avatar
                          sx={{
                            width: 22,
                            height: 22,
                            fontSize: '0.8rem',
                            color: '#ffffff',
                            backgroundColor: getTeamColor(group.name, teamColorMap).accent,
                            border: `1px solid ${getTeamColor(group.name, teamColorMap).border}`,
                          }}
                        >
                          <GroupIcon fontSize="inherit" />
                        </Avatar>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {group.name}
                        </Typography>
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        {group.users.map((user) => user.username).join(', ')}
                      </Typography>
                    </Box>
                    <IconButton
                      size="small"
                      color="secondary"
                      onClick={() => handleRemoveGroup(selectedShift, group.name)}
                      aria-label={`${group.name} entfernen`}
                    >
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  </DialogAssignmentRow>
                ))}

                {selectedShift.users?.map((user) => (
                  <DialogAssignmentRow key={`dialog-user-${user.id}`}>
                    <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', minWidth: 0 }}>
                      <PersonIcon color="action" fontSize="small" />
                      <Box sx={{ minWidth: 0 }}>
                        <Typography variant="body2">
                          {user.username}
                        </Typography>
                      </Box>
                    </Stack>
                    <IconButton
                      size="small"
                      onClick={() => handleRemoveUser(selectedShift, user.id)}
                      aria-label={`${user.username} entfernen`}
                    >
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  </DialogAssignmentRow>
                ))}

                {getCurrentStaff(selectedShift) === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    {translations.grid.noAssignments}
                  </Typography>
                )}
              </Stack>
            </Box>
          )}

          <TextField
            fullWidth
            placeholder={translations.grid.addDialogSearch}
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <Typography>{translations.grid.loadingAvailable}</Typography>
            </Box>
          ) : (
            <List sx={{ maxHeight: 400, overflow: 'auto' }}>
              {filteredGroups.length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ px: 2, py: 1, backgroundColor: 'grey.100' }}>
                    {translations.grid.addGroups}
                  </Typography>
                  {filteredGroups.map((group) => (
                    <ListItem key={`group-${group.id}`} disablePadding>
                      <ListItemButton onClick={() => handleAddGroup(group.id)}>
                        <ListItemAvatar>
                          <Avatar
                            sx={{
                              color: '#ffffff',
                              backgroundColor: getTeamColor(group.name, teamColorMap).accent,
                              border: `1px solid ${getTeamColor(group.name, teamColorMap).border}`,
                            }}
                          >
                            <GroupIcon />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={group.name}
                          secondary={`${group.users?.length || 0} Personen • ${group.users?.map((user) => user.username).join(', ') || ''}`}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                  {filteredUsers.length > 0 && <Divider sx={{ my: 1 }} />}
                </>
              )}

              {filteredUsers.length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ px: 2, py: 1, backgroundColor: 'grey.100' }}>
                    {translations.grid.addIndividuals}
                  </Typography>
                  {filteredUsers.map((user) => (
                    <ListItem key={user.id} disablePadding>
                      <ListItemButton onClick={() => handleAddUser(user.id)}>
                        <ListItemAvatar>
                          <Avatar>
                            <PersonIcon />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={user.username}
                          secondary={user.email}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </>
              )}

              {filteredUsers.length === 0 && filteredGroups.length === 0 && !loading && (
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  <Typography color="text.secondary">
                    {searchTerm
                      ? translations.grid.noSearchResults
                      : translations.grid.noAvailablePeople}
                  </Typography>
                </Box>
              )}
            </List>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setAddUserDialogOpen(false)}>
            {translations.cancel}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CoordinatorShiftGrid;
