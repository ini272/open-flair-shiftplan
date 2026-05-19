import React, { useMemo } from 'react';
import {
  Box,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import { alpha, styled } from '@mui/material/styles';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import { translations } from '../utils/translations';

const ShiftStateCard = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'isAvailable' && prop !== 'isAssigned',
})(({ theme, isAvailable, isAssigned }) => ({
  padding: theme.spacing(0.95, 1.05),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: isAvailable ? theme.palette.success.light : theme.palette.error.light,
  color: isAvailable ? theme.palette.success.contrastText : theme.palette.error.contrastText,
  boxShadow: isAssigned
    ? '0 0 0 2px rgba(0, 0, 0, 0.85)'
    : '0 1px 3px rgba(0, 0, 0, 0.12)',
  border: isAssigned
    ? `2px solid ${theme.palette.common.black}`
    : `1px solid ${alpha(theme.palette.common.black, 0.08)}`,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  minHeight: 42,
  gap: theme.spacing(0.75),
  fontWeight: 500,
}));

const formatTime = (dateTimeStr) => {
  const date = new Date(dateTimeStr);
  return date.toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
};

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('de-DE', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
};

const getSortMinutes = (timeStr) => {
  const [hours, minutes] = timeStr.split(':').map(Number);
  return (hours < 6 ? hours + 24 : hours) * 60 + minutes;
};

const getShiftLocationOrder = (title) => {
  const normalizedTitle = title.toLowerCase();

  if (normalizedTitle.includes('wein')) {
    return 0;
  }

  if (normalizedTitle.includes('bier')) {
    return 1;
  }

  return 2;
};

const getCompactShiftLabel = (title) => {
  const normalizedTitle = title.toLowerCase();

  if (normalizedTitle.includes('weinzelt')) {
    return 'WZ';
  }

  if (normalizedTitle.includes('bierwagen')) {
    return 'BW';
  }

  return title;
};

const CoordinatorPersonView = ({
  shifts,
  selectedViewOption,
  generatedAssignments,
  userOptOuts,
  groupOptOuts,
  loadingSelectionContext,
}) => {
  const assignmentMap = useMemo(() => {
    const map = new Map();

    if (!selectedViewOption) {
      return map;
    }

    (generatedAssignments || []).forEach((assignment) => {
      if (selectedViewOption.type === 'user' && assignment.user_id === selectedViewOption.id) {
        map.set(assignment.shift_id, assignment);
      }

      if (
        selectedViewOption.type === 'group'
        && assignment.assigned_via === 'group'
        && assignment.group_name === selectedViewOption.label
      ) {
        map.set(assignment.shift_id, assignment);
      }
    });

    return map;
  }, [generatedAssignments, selectedViewOption]);

  const optedOutShiftIds = useMemo(() => {
    if (!selectedViewOption) {
      return new Set();
    }

    const source = selectedViewOption.type === 'group'
      ? groupOptOuts[selectedViewOption.id] || []
      : userOptOuts[selectedViewOption.id] || [];

    return new Set(source.map((shift) => shift.id));
  }, [groupOptOuts, selectedViewOption, userOptOuts]);

  const { days, timeSlots, shiftsByDayAndTime } = useMemo(() => {
    const uniqueDays = new Set();
    const uniqueTimeSlots = new Set();
    const shiftMap = {};

    shifts.forEach((shift) => {
      const startDate = new Date(shift.start_time);
      const dayKey = startDate.toISOString().split('T')[0];
      const timeSlot = `${formatTime(shift.start_time)} - ${formatTime(shift.end_time)}`;
      const key = `${dayKey}-${timeSlot}`;

      uniqueDays.add(dayKey);
      uniqueTimeSlots.add(timeSlot);

      if (!shiftMap[key]) {
        shiftMap[key] = [];
      }

      shiftMap[key].push(shift);
    });

    return {
      days: Array.from(uniqueDays).sort(),
      timeSlots: Array.from(uniqueTimeSlots).sort((a, b) => (
        getSortMinutes(a.split(' - ')[0]) - getSortMinutes(b.split(' - ')[0])
      )),
      shiftsByDayAndTime: shiftMap,
    };
  }, [shifts]);

  if (!selectedViewOption) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          {translations.coordinator.noPersonSelected}
        </Typography>
      </Paper>
    );
  }

  if (loadingSelectionContext) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Stack spacing={1.5} sx={{ alignItems: 'center' }}>
          <CircularProgress size={28} />
          <Typography variant="body1" color="text.secondary">
            {translations.coordinator.loadingPeople}
          </Typography>
        </Stack>
      </Paper>
    );
  }

  if (shifts.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          {translations.grid.noShiftsAvailable}
        </Typography>
      </Paper>
    );
  }

  return (
    <TableContainer component={Paper} sx={{ overflowX: 'auto', borderRadius: 2.5 }}>
      <Table sx={{ minWidth: 980 }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: 150, backgroundColor: '#f5f5f5', fontWeight: 700 }}>
              {translations.grid.time}
            </TableCell>
            {days.map((day) => (
              <TableCell
                key={day}
                align="center"
                sx={{ backgroundColor: '#f5f5f5', minWidth: 190, fontWeight: 700 }}
              >
                {formatDate(day)}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {timeSlots.map((timeSlot) => (
            <TableRow key={timeSlot} hover>
              <TableCell sx={{ backgroundColor: '#fafafa', fontWeight: 700 }}>
                {timeSlot}
              </TableCell>
              {days.map((day) => {
                const dayShifts = [...(shiftsByDayAndTime[`${day}-${timeSlot}`] || [])]
                  .sort((a, b) => getShiftLocationOrder(a.title) - getShiftLocationOrder(b.title));

                return (
                  <TableCell key={`${day}-${timeSlot}`} sx={{ p: 1 }}>
                    <Box
                      sx={{
                        display: 'grid',
                        gridTemplateColumns: dayShifts.length > 1
                          ? 'repeat(2, minmax(0, 1fr))'
                          : 'minmax(0, 1fr)',
                        gap: 1,
                      }}
                    >
                      {dayShifts.map((shift) => {
                        const assignment = assignmentMap.get(shift.id);
                        const isAvailable = !optedOutShiftIds.has(shift.id);
                        const assignmentTitle = assignment
                          ? (assignment.assigned_via === 'group' && assignment.group_name
                            ? `${translations.coordinator.userAssignedVia} ${assignment.group_name}`
                            : translations.coordinator.userAssignedDirectly)
                          : (isAvailable
                            ? translations.coordinator.userAvailable
                            : translations.coordinator.userOptedOut);
                        const tooltipTitle = `${shift.title} • ${assignmentTitle}`;

                        return (
                          <Tooltip key={shift.id} title={tooltipTitle}>
                            <ShiftStateCard
                              isAvailable={isAvailable}
                              isAssigned={Boolean(assignment)}
                            >
                              <Typography
                                variant="body2"
                                sx={{
                                  minWidth: 0,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                  fontWeight: 600,
                                  fontSize: '0.84rem',
                                }}
                              >
                                {getCompactShiftLabel(shift.title)}
                              </Typography>

                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                                {assignment && (
                                  <AssignmentTurnedInIcon
                                    fontSize="small"
                                    sx={{ color: 'common.black' }}
                                  />
                                )}
                                {isAvailable ? <CheckIcon fontSize="small" /> : <CloseIcon fontSize="small" />}
                              </Box>
                            </ShiftStateCard>
                          </Tooltip>
                        );
                      })}
                    </Box>
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default CoordinatorPersonView;
