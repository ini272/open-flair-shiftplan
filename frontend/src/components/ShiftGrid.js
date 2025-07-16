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
  shouldForwardProp: (prop) => prop !== 'isPending' && prop !== 'selected'
})(({ theme, selected, isPending }) => ({
  padding: theme.spacing(1.5),
  margin: theme.spacing(0.5),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: selected ? theme.palette.success.light : theme.palette.error.light,
  color: selected ? theme.palette.success.contrastText : theme.palette.error.contrastText,
  cursor: isPending ? 'wait' : 'pointer',
  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
  boxShadow: isPending 
    ? '0 0 0 2px rgba(25, 118, 210, 0.5)' 
    : '0 1px 3px rgba(0,0,0,0.12)',
  '&:hover': {
    boxShadow: isPending 
      ? '0 0 0 2px rgba(25, 118, 210, 0.5)'
      : '0 4px 8px rgba(0,0,0,0.2)',
    transform: isPending ? 'none' : 'translateY(-2px)',
  },
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  minHeight: '40px',
  fontWeight: 500,
  // More pronounced visual feedback for pending operations
  opacity: isPending ? 0.8 : 1,
  position: 'relative',
  overflow: 'hidden',
  // Add a subtle pulse animation when pending
  animation: isPending ? 'pulse 1.5s infinite' : 'none',
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
  onTogglePreference,
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

  // Handle shift click with debounce to prevent double-clicks
  const handleShiftClick = useCallback((shiftId) => {
    // If already pending, don't allow another click
    if (isShiftPending(shiftId)) return;
    
    // Call the toggle preference function
    onTogglePreference(shiftId);
  }, [isShiftPending, onTogglePreference]);

  // Get day selection status for batch button styling
  const getDaySelectionStatus = useCallback((day) => {
    const dayShifts = shiftsByDay[day] || [];
    if (dayShifts.length === 0) return 'none';
    
    const selectedCount = dayShifts.filter(shift => isAvailable(shift.id)).length;
    
    if (selectedCount === 0) return 'none';
    if (selectedCount === dayShifts.length) return 'all';
    return 'partial';
  }, [shiftsByDay, isAvailable]);

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
              
              return (
                <TableCell key={day} align="center" sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5', minWidth: '180px' }}>
                  <Stack spacing={1} alignItems="center">
                    {formatDate(day)}
                    {dayShifts.length > 0 && onBatchDayToggle && (
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
                
                return (
                  <TableCell key={`${day}-${timeSlot}`} align="center" sx={{ padding: 1 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {cellShifts.map(shift => {
                        const available = isAvailable(shift.id);
                        const isPending = isShiftPending(shift.id);
                        
                        return (
                          <ShiftCell
                            key={shift.id}
                            selected={available}
                            isPending={isPending}
                            onClick={() => handleShiftClick(shift.id)}
                          >
                            <span>{shift.title}</span>
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

export default React.memo(ShiftGrid);