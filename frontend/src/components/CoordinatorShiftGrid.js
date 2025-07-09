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
  Stack,
  Tooltip
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PersonIcon from '@mui/icons-material/Person';
import CloseIcon from '@mui/icons-material/Close';
import { translations } from '../utils/translations';
import { shiftService } from '../services/api';

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
    'Mon': translations.days?.mon || 'Mon',
    'Tue': translations.days?.tue || 'Tue',
    'Wed': translations.days?.wed || 'Wed',
    'Thu': translations.days?.thu || 'Thu',
    'Fri': translations.days?.fri || 'Fri',
    'Sat': translations.days?.sat || 'Sat',
    'Sun': translations.days?.sun || 'Sun'
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
  height: 28,
  fontSize: '0.75rem',
  margin: theme.spacing(0.25),
  '& .MuiChip-avatar': {
    width: 20,
    height: 20,
    fontSize: '0.7rem',
  },
  '& .MuiChip-deleteIcon': {
    width: 16,
    height: 16,
    '&:hover': {
      color: theme.palette.error.main,
    },
  },
}));

const CoordinatorShiftGrid = ({ shifts, generatedAssignments, onAssignmentsChange }) => {
  // Merge shifts with generated assignments
  const shiftsWithAssignments = useMemo(() => {
    if (!generatedAssignments) return shifts;
    
    return shifts.map(shift => {
      const shiftAssignments = generatedAssignments.filter(
        assignment => assignment.shift_id === shift.id
      );
      
      const assignedUsers = shiftAssignments.map(assignment => ({
        id: assignment.user_id,
        username: assignment.username,
        assignedVia: assignment.assigned_via,
        groupName: assignment.group_name
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

  // Handle removing a user from a shift
  const handleRemoveUser = async (shiftId, userId, username) => {
    try {
      console.log(`Attempting to remove user ${username} (ID: ${userId}) from shift ${shiftId}`);
      
      // Add confirmation dialog
      if (!window.confirm(`Are you sure you want to remove ${username} from this shift?`)) {
        return;
      }
      
      const response = await shiftService.removeUserFromShift(shiftId, userId);
      console.log('Remove user response:', response);
      
      // Notify parent component to refresh assignments
      if (onAssignmentsChange) {
        console.log('Calling onAssignmentsChange to refresh...');
        await onAssignmentsChange();
      }
      
      console.log(`Successfully removed user ${username} from shift`);
    } catch (error) {
      console.error('Failed to remove user from shift:', error);
      console.error('Error details:', error.response?.data || error.message);
      
      // Show more detailed error message
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error';
      alert(`Failed to remove ${username} from shift: ${errorMessage}`);
    }
  };

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
      case 'empty': return translations.grid?.empty || 'Empty';
      case 'understaffed': return translations.grid?.understaffed || 'Understaffed';
      case 'partial': return translations.grid?.partial || 'Partial';
      case 'full': return translations.grid?.fullyStaffed || 'Full';
      case 'overstaffed': return translations.grid?.overstaffed || 'Overstaffed';
      default: return translations.grid?.empty || 'Empty';
    }
  };

  if (shiftsWithAssignments.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          {translations.grid?.noShiftsAvailable || 'No shifts available'}
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
          <Chip size="small" label={getStaffingText('empty')} color="default" />
          <Chip size="small" label={getStaffingText('understaffed')} color="error" />
          <Chip size="small" label={getStaffingText('partial')} color="warning" />
          <Chip size="small" label={getStaffingText('full')} color="success" />
          <Chip size="small" label={getStaffingText('overstaffed')} color="info" />
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
                  <Grid item xs={12} sm={6} md={4} xl={3} key={shift.id}>
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
                          <strong>{translations.shifts?.capacity || 'Capacity'}:</strong> {currentStaff}/{shift.capacity || '∞'}
                        </Typography>
                        
                        {/* Assigned Users */}
                        {currentStaff > 0 ? (
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                              {translations.shifts?.assignedUsers || 'Assigned Users'}:
                            </Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                              {shift.users.map(user => (
                                <UserChip
                                  key={user.id}
                                  avatar={<Avatar><PersonIcon fontSize="small" /></Avatar>}
                                  label={user.username}
                                  size="small"
                                  variant="outlined"
                                  color={user.assignedVia === 'group' ? 'secondary' : 'primary'}
                                  onDelete={(event) => {
                                    event.preventDefault();
                                    event.stopPropagation();
                                    console.log('Delete button clicked for user:', user.username);
                                    handleRemoveUser(shift.id, user.id, user.username);
                                  }}
                                  deleteIcon={
                                    <Tooltip title={`Remove ${user.username} from shift`}>
                                      <CloseIcon />
                                    </Tooltip>
                                  }
                                />
                              ))}
                            </Box>
                            
                            {/* Show group assignments info */}
                            {shift.users.some(user => user.assignedVia === 'group') && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}>
                                Note: Users assigned via groups may be re-added when generating new plans
                              </Typography>
                            )}
                          </Box>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            {translations.grid?.noAssignments || 'No assignments'}
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