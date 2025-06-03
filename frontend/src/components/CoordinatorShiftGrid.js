import React, { useMemo } from 'react';
import {
  Box,
  Typography,
  Chip,
  Card,
  CardContent,
  Grid,
  Paper,
  Avatar,
  Stack
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PersonIcon from '@mui/icons-material/Person';
import GroupIcon from '@mui/icons-material/Group';

// Format functions (same as ShiftGrid)
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
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
}

const ShiftCard = styled(Card)(({ theme, staffingLevel }) => {
  let backgroundColor, borderColor;
  
  switch (staffingLevel) {
    case 'empty':
      backgroundColor = theme.palette.grey[100];
      borderColor = theme.palette.grey[400];
      break;
    case 'understaffed':
      backgroundColor = theme.palette.error.light + '20';
      borderColor = theme.palette.error.main;
      break;
    case 'partial':
      backgroundColor = theme.palette.warning.light + '20';
      borderColor = theme.palette.warning.main;
      break;
    case 'full':
      backgroundColor = theme.palette.success.light + '20';
      borderColor = theme.palette.success.main;
      break;
    case 'overstaffed':
      backgroundColor = theme.palette.info.light + '20';
      borderColor = theme.palette.info.main;
      break;
    default:
      backgroundColor = theme.palette.grey[50];
      borderColor = theme.palette.grey[300];
  }
  
  return {
    minHeight: 120,
    border: `2px solid ${borderColor}`,
    backgroundColor,
    transition: 'all 0.2s ease-in-out',
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: theme.shadows[4],
    },
  };
});

const UserChip = styled(Chip)(({ theme }) => ({
  height: 24,
  fontSize: '0.75rem',
  '& .MuiChip-avatar': {
    width: 20,
    height: 20,
    fontSize: '0.7rem',
  },
}));

const CoordinatorShiftGrid = ({ shifts, generatedAssignments }) => {
  // Merge shifts with generated assignments
  const shiftsWithAssignments = useMemo(() => {
    if (!generatedAssignments) return shifts;
    
    return shifts.map(shift => {
      // Find assignments for this shift
      const shiftAssignments = generatedAssignments.filter(
        assignment => assignment.shift_id === shift.id
      );
      
      // Create user objects from assignments
      const assignedUsers = shiftAssignments.map(assignment => ({
        id: assignment.user_id,
        username: assignment.username
      }));
      
      return {
        ...shift,
        users: assignedUsers
      };
    });
  }, [shifts, generatedAssignments]);

  // Pre-compute grid data
  const { days, timeSlots, shiftsByDayAndTime } = useMemo(() => {
    const uniqueDays = new Set();
    const uniqueTimeSlots = new Set();
    const shiftMap = {};
    
    shiftsWithAssignments.forEach(shift => {
      const startDate = new Date(shift.start_time);
      const dateKey = startDate.toISOString().split('T')[0];
      uniqueDays.add(dateKey);
      
      const timeSlot = `${formatTime(shift.start_time)} - ${formatTime(shift.end_time)}`;
      uniqueTimeSlots.add(timeSlot);
      
      const key = `${dateKey}-${timeSlot}`;
      if (!shiftMap[key]) {
        shiftMap[key] = [];
      }
      shiftMap[key].push(shift);
    });
    
    const sortedDays = Array.from(uniqueDays).sort();
    const sortedTimeSlots = Array.from(uniqueTimeSlots).sort();
    
    return {
      days: sortedDays,
      timeSlots: sortedTimeSlots,
      shiftsByDayAndTime: shiftMap
    };
  }, [shiftsWithAssignments]);

  const getStaffingLevel = (shift) => {
    const assignedCount = shift.users?.length || 0;
    const capacity = shift.capacity;
    
    if (assignedCount === 0) return 'empty';
    if (!capacity) return assignedCount > 0 ? 'partial' : 'empty';
    
    const ratio = assignedCount / capacity;
    if (ratio >= 1) return assignedCount > capacity ? 'overstaffed' : 'full';
    if (ratio >= 0.5) return 'partial';
    return 'understaffed';
  };

  const getStaffingColor = (level) => {
    switch (level) {
      case 'empty': return 'default';
      case 'understaffed': return 'error';
      case 'partial': return 'warning';
      case 'full': return 'success';
      case 'overstaffed': return 'info';
      default: return 'default';
    }
  };

  const renderShiftCell = (day, timeSlot) => {
    const key = `${day}-${timeSlot}`;
    const shiftsInCell = shiftsByDayAndTime[key] || [];
    
    if (shiftsInCell.length === 0) {
      return (
        <Box sx={{ minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="body2" color="text.disabled">
            No shifts
          </Typography>
        </Box>
      );
    }
    
    return (
      <Stack spacing={1}>
        {shiftsInCell.map(shift => {
          const staffingLevel = getStaffingLevel(shift);
          const assignedCount = shift.users?.length || 0;
          const capacity = shift.capacity || '∞';
          
          return (
            <ShiftCard key={shift.id} staffingLevel={staffingLevel}>
              <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                {/* Shift Title and Capacity */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', fontSize: '0.85rem' }}>
                    {shift.title}
                  </Typography>
                  <Chip
                    size="small"
                    label={`${assignedCount}/${capacity}`}
                    color={getStaffingColor(staffingLevel)}
                    variant="outlined"
                    sx={{ height: 20, fontSize: '0.7rem' }}
                  />
                </Box>
                
                {/* Assigned Users */}
                {shift.users && shift.users.length > 0 ? (
                  <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
                    {shift.users.map(user => (
                      <UserChip
                        key={user.id}
                        avatar={<Avatar sx={{ bgcolor: 'primary.main' }}>{user.username[0].toUpperCase()}</Avatar>}
                        label={user.username}
                        size="small"
                        variant="filled"
                        color="primary"
                      />
                    ))}
                  </Stack>
                ) : (
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 40 }}>
                    <Typography variant="body2" color="text.disabled" sx={{ fontSize: '0.75rem' }}>
                      No assignments
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </ShiftCard>
          );
        })}
      </Stack>
    );
  };

  if (days.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No shifts available
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ width: '100%', overflowX: 'auto' }}>
      {/* Legend */}
      <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Chip size="small" label="Empty" color="default" variant="outlined" />
        <Chip size="small" label="Under-staffed" color="error" variant="outlined" />
        <Chip size="small" label="Partial" color="warning" variant="outlined" />
        <Chip size="small" label="Fully staffed" color="success" variant="outlined" />
        <Chip size="small" label="Over-staffed" color="info" variant="outlined" />
      </Box>

      <Grid container spacing={1}>
        {/* Header Row */}
        <Grid item xs={2}>
          <Box sx={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              Time
            </Typography>
          </Box>
        </Grid>
        {days.map(day => (
          <Grid item xs={2} key={day}>
            <Paper sx={{ p: 1, textAlign: 'center', bgcolor: 'primary.main', color: 'white' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                {formatDate(day)}
              </Typography>
            </Paper>
          </Grid>
        ))}

        {/* Time Slot Rows */}
        {timeSlots.map(timeSlot => (
          <React.Fragment key={timeSlot}>
            {/* Time Label */}
            <Grid item xs={2}>
              <Box sx={{ 
                height: '100%', 
                minHeight: 120,
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                bgcolor: 'grey.100',
                borderRadius: 1
              }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', textAlign: 'center' }}>
                  {timeSlot}
                </Typography>
              </Box>
            </Grid>
            
            {/* Shift Cells */}
            {days.map(day => (
              <Grid item xs={2} key={`${day}-${timeSlot}`}>
                {renderShiftCell(day, timeSlot)}
              </Grid>
            ))}
          </React.Fragment>
        ))}
      </Grid>
    </Box>
  );
};

export default CoordinatorShiftGrid;