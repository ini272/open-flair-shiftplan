import React, { useMemo, useCallback } from 'react';
import { 
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Box,
  CircularProgress, Button, Stack
} from '@mui/material';
import { styled } from '@mui/material/styles';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import { translations } from '../utils/translations';

// Enhanced styled component for shift cells with more pronounced visual feedback
const ShiftCell = styled(Box, {
  shouldForwardProp: (prop) => !['isPending', 'selected', 'blocked'].includes(prop)
})(({ theme, selected, isPending, blocked }) => ({
  padding: theme.spacing(1, 1.1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: blocked
    ? theme.palette.grey[300]
    : (selected ? theme.palette.success.light : theme.palette.error.light),
  color: blocked
    ? theme.palette.text.secondary
    : (selected ? theme.palette.success.contrastText : theme.palette.error.contrastText),
  cursor: blocked ? 'not-allowed' : (isPending ? 'wait' : 'pointer'),
  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
  boxShadow: isPending 
    ? '0 0 0 2px rgba(25, 118, 210, 0.5)' 
    : '0 1px 3px rgba(0,0,0,0.12)',
  '&:hover': {
    boxShadow: blocked
      ? '0 1px 3px rgba(0,0,0,0.12)'
      : (isPending 
      ? '0 0 0 2px rgba(25, 118, 210, 0.5)'
      : '0 4px 8px rgba(0,0,0,0.2)'),
    transform: blocked || isPending ? 'none' : 'translateY(-2px)',
  },
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  minHeight: '46px',
  fontWeight: 500,
  gap: theme.spacing(0.75),
  // More pronounced visual feedback for pending operations
  opacity: isPending ? 0.8 : 1,
  position: 'relative',
  overflow: 'hidden',
  // Add a subtle pulse animation when pending
  animation: isPending && !blocked ? 'pulse 1.5s infinite' : 'none',
  '@keyframes pulse': {
    '0%': { opacity: 0.7 },
    '50%': { opacity: 0.9 },
    '100%': { opacity: 0.7 }
  }
}));

// Move format functions outside component
function formatTime(dateTimeStr) {
  const date = new Date(dateTimeStr);
  return date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('de-DE', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
}

const ShiftGrid = ({ 
  shifts, 
  userPreferences, 
  blockedShiftIds = [],
  pendingOperations = {},
  onBatchDayToggle, // New prop for batch operations
  batchPendingDays = {} // New prop to track which days are being batch processed
}) => {
  // Create a lookup object for user preferences for O(1) lookups
  const preferenceMap = useMemo(() => {
    const map = {};
    userPreferences.forEach(id => {
      map[id] = true;
    });
    return map;
  }, [userPreferences]);

  // Create a lookup object for pending operations for O(1) lookups
  const pendingMap = useMemo(() => {
    return { ...pendingOperations };
  }, [pendingOperations]);

  const blockedShiftIdSet = useMemo(() => new Set(blockedShiftIds), [blockedShiftIds]);

  // Extract unique days and time slots from the shifts using smart grouping
  const { days, timeSlots, shiftsByDayAndTime, shiftsByDay } = useMemo(() => {
    const uniqueDays = new Set();
    const uniqueTimeSlots = new Set();
    const shiftMap = {};
    const dayShiftMap = {};
    
    shifts.forEach(shift => {
      const startDate = new Date(shift.start_time);
      // Use actual date, not display date
      const dateKey = startDate.toISOString().split('T')[0];
      uniqueDays.add(dateKey);
      
      const timeSlot = `${formatTime(shift.start_time)} - ${formatTime(shift.end_time)}`;
      uniqueTimeSlots.add(timeSlot);
      
      const key = `${dateKey}-${timeSlot}`;
      if (!shiftMap[key]) {
        shiftMap[key] = [];
      }
      shiftMap[key].push(shift);
      
      if (!dayShiftMap[dateKey]) {
        dayShiftMap[dateKey] = [];
      }
      dayShiftMap[dateKey].push(shift);
    });
    
    const sortedDays = Array.from(uniqueDays).sort();
    
    // Sort time slots chronologically with smart late-night handling
    const sortedTimeSlots = Array.from(uniqueTimeSlots).sort((a, b) => {
      const timeA = a.split(' - ')[0];
      const timeB = b.split(' - ')[0];
      
      // Convert to minutes for smart sorting
      const getMinutes = (timeStr) => {
        const [hours, minutes] = timeStr.split(':').map(Number);
        // Treat early morning hours (00:xx - 05:xx) as late night (add 24 hours)
        return hours < 6 ? (hours + 24) * 60 + minutes : hours * 60 + minutes;
      };
      
      return getMinutes(timeA) - getMinutes(timeB);
    });
    
    return {
      days: sortedDays,
      timeSlots: sortedTimeSlots,
      shiftsByDayAndTime: shiftMap,
      shiftsByDay: dayShiftMap
    };
  }, [shifts]);

  // Find shifts for a specific day and time slot - use the precomputed map
  const findShifts = useCallback((day, timeSlot) => {
    const key = `${day}-${timeSlot}`;
    return shiftsByDayAndTime[key] || [];
  }, [shiftsByDayAndTime]);

  // Check if a shift is available - use the preference map for O(1) lookup
  const isAvailable = useCallback((shiftId) => {
    return preferenceMap[shiftId] === true;
  }, [preferenceMap]);

  // Check if a shift has a pending operation - use the pending map for O(1) lookup
  const isShiftPending = useCallback((shiftId) => {
    return pendingMap[shiftId] !== undefined;
  }, [pendingMap]);

  const isShiftBlocked = useCallback((shiftId) => {
    return blockedShiftIdSet.has(shiftId);
  }, [blockedShiftIdSet]);

  const getSlotSelectionStatus = useCallback((slotShifts) => {
    if (slotShifts.length === 0) {
      return 'none';
    }

    if (slotShifts.every((shift) => isShiftBlocked(shift.id))) {
      return 'blocked';
    }

    return slotShifts.some((shift) => !isShiftBlocked(shift.id) && isAvailable(shift.id)) ? 'all' : 'none';
  }, [isAvailable, isShiftBlocked]);

  const handleSlotClick = useCallback((slotShifts) => {
    if (!onBatchDayToggle || slotShifts.length === 0) {
      return;
    }

    if (slotShifts.some(shift => isShiftPending(shift.id))) {
      return;
    }

    const selectionStatus = getSlotSelectionStatus(slotShifts);
    if (selectionStatus === 'blocked') {
      return;
    }
    const shouldSelect = selectionStatus === 'none';

    onBatchDayToggle(slotShifts, shouldSelect);
  }, [getSlotSelectionStatus, isShiftPending, onBatchDayToggle]);

  // Get day selection status for batch button styling
  const getDaySelectionStatus = useCallback((day) => {
    const dayShifts = shiftsByDay[day] || [];
    if (dayShifts.length === 0) return 'none';

    const slotStatuses = timeSlots
      .map(timeSlot => findShifts(day, timeSlot))
      .filter(slotShifts => slotShifts.length > 0)
      .map(slotShifts => getSlotSelectionStatus(slotShifts))
      .filter((status) => status !== 'blocked');

    if (slotStatuses.length === 0) return 'none';
    if (slotStatuses.every(status => status === 'all')) return 'all';
    if (slotStatuses.every(status => status === 'none')) return 'none';
    return 'partial';
  }, [findShifts, getSlotSelectionStatus, shiftsByDay, timeSlots]);

  // Handle batch day toggle
  const handleBatchDayToggle = useCallback((day) => {
    if (!onBatchDayToggle) return;
    
    const dayShifts = shiftsByDay[day] || [];
    if (dayShifts.length === 0) return;
    
    const selectionStatus = getDaySelectionStatus(day);
    const shouldSelect = selectionStatus !== 'all'; // Select all if not all are selected
    
    onBatchDayToggle(dayShifts, shouldSelect);
  }, [shiftsByDay, getDaySelectionStatus, onBatchDayToggle]);

  return (
    <TableContainer component={Paper} sx={{ overflowX: 'auto' }}>
      <Table sx={{ minWidth: 650 }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: '150px', backgroundColor: '#f5f5f5' }}>
              {translations.grid.timeSlot}
            </TableCell>
            {days.map(day => {
              const selectionStatus = getDaySelectionStatus(day);
              const isDayPending = batchPendingDays[day];
              const dayShifts = shiftsByDay[day] || [];
              const hasActionableShifts = dayShifts.some((shift) => !isShiftBlocked(shift.id));
              
              return (
                <TableCell key={day} align="center" sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5', minWidth: '180px' }}>
                  <Stack spacing={1} alignItems="center">
                    {formatDate(day)}
                    {dayShifts.length > 0 && onBatchDayToggle && hasActionableShifts && (
                      <Button
                        size="small"
                        variant={selectionStatus === 'all' ? 'contained' : 'outlined'}
                        color={selectionStatus === 'partial' ? 'warning' : 'primary'}
                        onClick={() => handleBatchDayToggle(day)}
                        disabled={isDayPending}
                        sx={{ 
                          minWidth: 'auto', 
                          px: 1, 
                          fontSize: '0.7rem',
                          textTransform: 'none'
                        }}
                      >
                        {isDayPending ? (
                          <CircularProgress size={12} />
                        ) : (
                          selectionStatus === 'all' ? 'Alle abwählen' : 'Alle auswählen'
                        )}
                      </Button>
                    )}
                  </Stack>
                </TableCell>
              );
            })}
          </TableRow>
        </TableHead>
        <TableBody>
          {timeSlots.map(timeSlot => (
            <TableRow key={timeSlot} hover>
              <TableCell sx={{ backgroundColor: '#fafafa' }}>{timeSlot}</TableCell>
              {days.map(day => {
                const cellShifts = findShifts(day, timeSlot);
                const selectionStatus = getSlotSelectionStatus(cellShifts);
                const available = selectionStatus === 'all';
                const blocked = selectionStatus === 'blocked';
                const isPending = cellShifts.some(shift => isShiftPending(shift.id));
                
                return (
                  <TableCell key={`${day}-${timeSlot}`} align="center" sx={{ padding: 1 }}>
                    {cellShifts.length > 0 ? (
                      <ShiftCell
                        selected={available}
                        blocked={blocked}
                        isPending={isPending}
                        onClick={() => handleSlotClick(cellShifts)}
                      >
                        <Box
                          component="span"
                          sx={{
                            minWidth: 0,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            fontSize: '0.86rem',
                            fontWeight: 600
                          }}
                        >
                          {blocked
                            ? translations.grid.slotAgeRestricted
                            : (available
                              ? translations.grid.slotAvailable
                              : translations.grid.slotUnavailable)}
                        </Box>
                        {isPending ? (
                          <CircularProgress 
                            size={16} 
                            thickness={5} 
                            sx={{ ml: 1 }} 
                          />
                        ) : (
                          available ? 
                            <CheckIcon fontSize="small" sx={{ ml: 1 }} /> : 
                            <CloseIcon fontSize="small" sx={{ ml: 1 }} />
                        )}
                      </ShiftCell>
                    ) : null}
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

export default React.memo(ShiftGrid);
