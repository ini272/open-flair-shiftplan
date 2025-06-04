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
import { translations } from '../utils/translations';

// Format functions
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
  const dayNames = {
    'Mon': translations.days.mon,
    'Tue': translations.days.tue,
    'Wed': translations.days.wed,
    'Thu': translations.days.thu,
    'Fri': translations.days.fri,
    'Sat': translations.days.sat,
    'Sun': translations.days.sun
  };
  
  const englishFormatted = date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
  
  // Replace English day with German
  const parts = englishFormatted.split(' ');
  const germanDay = dayNames[parts[0]] || parts[0];
  
  return `${germanDay} ${parts[1]} ${parts[2]}`;
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
      const shiftAssignments = generatedAssignments.filter(
        assignment => assignment.shift_id === shift.id
      );
      
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

  // Group shifts by date
  const shiftsByDate = useMemo(() => {
    const grouped = {};
    
    shiftsWithAssignments.forEach(shift => {
      const date = new Date(shift.start_time).toDateString();
      if (!grouped[date]) {
        grouped[date] = [];
      }
      grouped[date].push(shift);
    });
    
    // Sort shifts within each date by start time
    Object.keys(grouped).forEach(date => {
      grouped[date].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    });
    
    return grouped;
  }, [shiftsWithAssignments]);

  // Determine staffing level
  const getStaffingLevel = (shift) => {
    const currentStaff = shift.users ? shift.users.length : 0;
    const capacity = shift.capacity;
    
    if (currentStaff === 0) return 'empty';
    if (!capacity) return 'partial'; // No capacity set
    if (currentStaff < capacity * 0.5) return 'understaffed';
    if (currentStaff < capacity) return 'partial';
    if (currentStaff === capacity) return 'full';
    return 'overstaffed';
  };

  // Get staffing level color
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

  // Get staffing level text
  const getStaffingText = (level) => {
    switch (level) {
      case 'empty': return translations.grid.empty;
      case 'understaffed': return translations.grid.understaffed;
      case 'partial': return translations.grid.partial;
      case 'full': return translations.grid.fullyStaffed;
      case 'overstaffed': return translations.grid.overstaffed;
      default: return translations.grid.empty;
    }
  };

  if (shiftsWithAssignments.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          {translations.grid.noShiftsAvailable}
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Legend */}
      <Paper sx={{ p: 2, mb: 3, backgroundColor: 'grey.50' }}>
        <Typography variant="subtitle2" gutterBottom>
          Legende:
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Chip size="small" label={translations.grid.empty} color="default" />
          <Chip size="small" label={translations.grid.understaffed} color="error" />
          <Chip size="small" label={translations.grid.partial} color="warning" />
          <Chip size="small" label={translations.grid.fullyStaffed} color="success" />
          <Chip size="small" label={translations.grid.overstaffed} color="info" />
        </Stack>
      </Paper>

      {/* Shifts grouped by date */}
      {Object.entries(shiftsByDate)
        .sort(([a], [b]) => new Date(a) - new Date(b))
        .map(([date, dateShifts]) => (
          <Box key={date} sx={{ mb: 4 }}>
            <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
              {formatDate(date)}
            </Typography>
            
            <Grid container spacing={2}>
              {dateShifts.map(shift => {
                const staffingLevel = getStaffingLevel(shift);
                const currentStaff = shift.users ? shift.users.length : 0;
                
                return (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={shift.id}>
                    <ShiftCard staffingLevel={staffingLevel}>
                      <CardContent sx={{ p: 2 }}>
                        {/* Shift Header */}
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', lineHeight: 1.2 }}>
                            {shift.title}
                          </Typography>
                          <Chip 
                            size="small" 
                            label={getStaffingText(staffingLevel)}
                            color={getStaffingColor(staffingLevel)}
                          />
                        </Box>
                        
                        {/* Time */}
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
                        </Typography>
                        
                        {/* Capacity */}
                        <Typography variant="body2" sx={{ mb: 2 }}>
                          <strong>{translations.shifts.capacity}:</strong> {currentStaff}/{shift.capacity || '∞'}
                        </Typography>
                        
                        {/* Assigned Users */}
                        {currentStaff > 0 ? (
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                              {translations.shifts.assignedUsers}:
                            </Typography>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap">
                              {shift.users.slice(0, 3).map(user => (
                                <UserChip
                                  key={user.id}
                                  avatar={<Avatar><PersonIcon fontSize="small" /></Avatar>}
                                  label={user.username}
                                  size="small"
                                  variant="outlined"
                                />
                              ))}
                              {shift.users.length > 3 && (
                                <UserChip
                                  label={`+${shift.users.length - 3}`}
                                  size="small"
                                  color="primary"
                                />
                              )}
                            </Stack>
                          </Box>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            {translations.grid.noAssignments}
                          </Typography>
                        )}
                      </CardContent>
                    </ShiftCard>
                  </Grid>
                );
              })}
            </Grid>
          </Box>
        ))}
    </Box>
  );
};

export default CoordinatorShiftGrid;