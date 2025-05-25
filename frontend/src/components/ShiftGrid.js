import React, { useMemo } from 'react';
import { 
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Box,
  CircularProgress
} from '@mui/material';
import { styled } from '@mui/material/styles';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';

// Enhanced styled component for shift cells with more pronounced visual feedback
const ShiftCell = styled(Box)(({ theme, selected, isPending }) => ({
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

const ShiftGrid = ({ 
  shifts, 
  userPreferences, 
  onTogglePreference,
  pendingOperations = {}
}) => {
  // Extract unique days and time slots from the shifts
  const { days, timeSlots } = useMemo(() => {
    const uniqueDays = new Set();
    const uniqueTimeSlots = new Set();
    
    shifts.forEach(shift => {
      const startDate = new Date(shift.start_time);
      // Format: YYYY-MM-DD
      const dateKey = startDate.toISOString().split('T')[0];
      uniqueDays.add(dateKey);
      
      const timeSlot = `${formatTime(shift.start_time)} - ${formatTime(shift.end_time)}`;
      uniqueTimeSlots.add(timeSlot);
    });
    
    // Sort days chronologically
    const sortedDays = Array.from(uniqueDays).sort();
    
    // Sort time slots chronologically
    const sortedTimeSlots = Array.from(uniqueTimeSlots).sort((a, b) => {
      const timeA = a.split(' - ')[0];
      const timeB = b.split(' - ')[0];
      return new Date(`2000-01-01T${timeA}`) - new Date(`2000-01-01T${timeB}`);
    });
    
    return {
      days: sortedDays,
      timeSlots: sortedTimeSlots
    };
  }, [shifts]);

  // Format time for display in 24-hour format
  function formatTime(dateTimeStr) {
    const date = new Date(dateTimeStr);
    return date.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }

  // Format date for column headers
  function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
  }

  // Find shifts for a specific day and time slot
  function findShifts(day, timeSlot) {
    return shifts.filter(shift => {
      const startDate = new Date(shift.start_time);
      const dateKey = startDate.toISOString().split('T')[0];
      const shiftTimeSlot = `${formatTime(shift.start_time)} - ${formatTime(shift.end_time)}`;
      
      return dateKey === day && shiftTimeSlot === timeSlot;
    });
  }

  // Check if a shift is in the user's preferences
  function isPreferred(shiftId) {
    return userPreferences.includes(shiftId);
  }

  // Check if a shift has a pending operation
  function isShiftPending(shiftId) {
    return pendingOperations[shiftId] !== undefined;
  }

  // Handle shift click with debounce to prevent double-clicks
  const handleShiftClick = (shiftId) => {
    // If already pending, don't allow another click
    if (isShiftPending(shiftId)) return;
    
    // Call the toggle preference function
    onTogglePreference(shiftId);
  };

  return (
    <TableContainer component={Paper} sx={{ overflowX: 'auto' }}>
      <Table sx={{ minWidth: 650 }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: '150px', backgroundColor: '#f5f5f5' }}>Time Slot</TableCell>
            {days.map(day => (
              <TableCell key={day} align="center" sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>
                {formatDate(day)}
              </TableCell>
            ))}
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
                        const preferred = isPreferred(shift.id);
                        const isPending = isShiftPending(shift.id);
                        
                        return (
                          <ShiftCell
                            key={shift.id}
                            selected={preferred}
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
                              preferred ? 
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

export default ShiftGrid;