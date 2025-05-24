import React, { useMemo } from 'react';
import { 
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Box
} from '@mui/material';
import { styled } from '@mui/material/styles';

// Styled component for shift cells
const ShiftCell = styled(Box)(({ theme, selected }) => ({
  padding: theme.spacing(1.5),
  margin: theme.spacing(0.5),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: selected ? theme.palette.success.light : theme.palette.error.light,
  color: selected ? theme.palette.success.contrastText : theme.palette.error.contrastText,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
  '&:hover': {
    boxShadow: '0 3px 6px rgba(0,0,0,0.16)',
    opacity: 0.9,
  },
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  minHeight: '40px',
  fontWeight: 500,
}));

const ShiftGrid = ({ 
  shifts, 
  userPreferences, 
  onTogglePreference 
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
                        return (
                          <ShiftCell
                            key={shift.id}
                            selected={preferred}
                            onClick={() => onTogglePreference(shift.id)}
                          >
                            {shift.title}
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