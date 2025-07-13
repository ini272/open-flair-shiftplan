import React, { useMemo, useState } from 'react';
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
  Tooltip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  TextField,
  InputAdornment
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PersonIcon from '@mui/icons-material/Person';
import CloseIcon from '@mui/icons-material/Close';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import { translations } from '../utils/translations';
import { shiftService, userService } from '../services/api';

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

// Smart grouping: late night shifts (00:xx-05:xx) belong to previous day visually
function getShiftDisplayDate(shift) {
  const startTime = new Date(shift.start_time);
  const hour = startTime.getHours();
  
  // If shift starts between midnight and 6 AM, it belongs to previous day visually
  if (hour >= 0 && hour < 6) {
    const prevDay = new Date(startTime);
    prevDay.setDate(prevDay.getDate() - 1);
    return prevDay.toDateString();
  }
  
  return startTime.toDateString();
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
  // Force the label to use normal text color
  '& .MuiChip-label': {
    color: `${theme.palette.text.primary} !important`,
  },
  '& .MuiChip-avatar': {
    width: 20,
    height: 20,
    fontSize: '0.7rem',
  },
  '& .MuiChip-deleteIcon': {
    width: 16,
    height: 16,
    color: theme.palette.text.secondary,
    '&:hover': {
      color: theme.palette.error.main,
      backgroundColor: theme.palette.error.light + '30',
      borderRadius: '50%',
    },
  },
}));

const AddUserButton = styled(IconButton)(({ theme }) => ({
  width: 24,
  height: 24,
  backgroundColor: theme.palette.primary.light + '30',
  color: theme.palette.primary.main,
  border: `1px dashed ${theme.palette.primary.main}`,
  marginLeft: theme.spacing(1.5),
  '&:hover': {
    backgroundColor: theme.palette.primary.light + '50',
    transform: 'scale(1.1)',
  },
}));

const CoordinatorShiftGrid = ({ shifts, generatedAssignments, onAssignmentsChange }) => {
  const [addUserDialogOpen, setAddUserDialogOpen] = useState(false);
  const [selectedShift, setSelectedShift] = useState(null);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loadingUsers, setLoadingUsers] = useState(false);

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
      // Use smart display date instead of actual start date
      const date = getShiftDisplayDate(shift);
      if (!grouped[date]) {
        grouped[date] = [];
      }
      grouped[date].push(shift);
    });
    
    // Sort shifts within each date by start time with smart late-night handling
    Object.keys(grouped).forEach(date => {
      grouped[date].sort((a, b) => {
        const getMinutes = (dateTime) => {
          const time = new Date(dateTime);
          const hours = time.getHours();
          const minutes = time.getMinutes();
          // Treat early morning hours (0-5) as late night
          return hours < 6 ? (hours + 24) * 60 + minutes : hours * 60 + minutes;
        };
        
        return getMinutes(a.start_time) - getMinutes(b.start_time);
      });
    });
    
    return grouped;
  }, [shiftsWithAssignments]);

  // Handle opening the add user dialog
  const handleOpenAddUserDialog = async (shift) => {
    setSelectedShift(shift);
    setAddUserDialogOpen(true);
    setLoadingUsers(true);
    setSearchTerm('');

    try {
      // Get available users for this shift (not opted out)
      const response = await shiftService.getAvailableUsers(shift.id);
      
      // Filter out users already assigned to this shift
      const currentUserIds = new Set(shift.users?.map(u => u.id) || []);
      const filteredUsers = response.data.filter(user => !currentUserIds.has(user.id));
      
      setAvailableUsers(filteredUsers);
    } catch (error) {
      console.error('Failed to load available users:', error);
      setAvailableUsers([]);
    } finally {
      setLoadingUsers(false);
    }
  };

  // Handle adding a user to a shift
  const handleAddUser = async (userId, username) => {
    try {
      console.log(`Adding user ${username} (${userId}) to shift ${selectedShift.id}`);
      
      await shiftService.addUserToShift({
        shift_id: selectedShift.id,
        user_id: userId
      });
      
      // Close dialog and refresh assignments
      setAddUserDialogOpen(false);
      if (onAssignmentsChange) {
        await onAssignmentsChange();
      }
      
      console.log(`Successfully added user ${username} to shift`);
    } catch (error) {
      console.error('Failed to add user to shift:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error';
      alert(`Failed to add ${username} to shift: ${errorMessage}`);
    }
  };

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

  // Filter users based on search term
  const filteredAvailableUsers = useMemo(() => {
    if (!searchTerm) return availableUsers;
    
    return availableUsers.filter(user => 
      user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [availableUsers, searchTerm]);

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
                const hasCapacity = !shift.capacity || currentStaff < shift.capacity;
                
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
                        
                        {/* Capacity with Add Button */}
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                          <Typography variant="body2">
                            <strong>{translations.shifts?.capacity || 'Capacity'}:</strong> {currentStaff}/{shift.capacity || '∞'}
                          </Typography>
                          
                          {/* Add user button next to capacity */}
                          {hasCapacity && (
                            <Tooltip title="Add user to shift">
                              <AddUserButton
                                onClick={() => handleOpenAddUserDialog(shift)}
                                size="small"
                              >
                                <AddIcon fontSize="small" />
                              </AddUserButton>
                            </Tooltip>
                          )}
                        </Box>
                        
                        {/* Assigned Users */}
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                            {translations.shifts?.assignedUsers || 'Assigned Users'}:
                          </Typography>
                          
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                            {/* Alternative approach - completely neutral styling */}
                            {shift.users?.map(user => (
                              <UserChip
                                key={user.id}
                                avatar={<Avatar><PersonIcon fontSize="small" /></Avatar>}
                                label={user.username}
                                size="small"
                                variant="outlined"
                                // Use default styling with custom border only
                                sx={{
                                  borderColor: user.assignedVia === 'group' 
                                    ? 'secondary.main' 
                                    : 'primary.main',
                                  backgroundColor: 'background.paper',
                                  '& .MuiChip-label': {
                                    color: 'text.primary !important',
                                  },
                                  '& .MuiChip-avatar': {
                                    backgroundColor: 'grey.300',
                                    color: 'grey.700',
                                  },
                                }}
                                onDelete={(event) => {
                                  event.preventDefault();
                                  event.stopPropagation();
                                  handleRemoveUser(shift.id, user.id, user.username);
                                }}
                                deleteIcon={<CloseIcon />}
                              />
                            ))}
                          </Box>
                          
                          {/* Show group assignments info */}
                          {shift.users?.some(user => user.assignedVia === 'group') && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}>
                              Note: Users assigned via groups may be re-added when generating new plans
                            </Typography>
                          )}
                          
                          {/* Show message if no users */}
                          {(!shift.users || shift.users.length === 0) && (
                            <Typography variant="caption" color="text.secondary">
                              {translations.grid?.noAssignments || 'No assignments'}
                            </Typography>
                          )}
                        </Box>
                      </CardContent>
                    </ShiftCard>
                  </Grid>
                );
              })}
            </Grid>
          </Box>
        ))}

      {/* Add User Dialog */}
      <Dialog 
        open={addUserDialogOpen} 
        onClose={() => setAddUserDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Add User to {selectedShift?.title}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ mb: 2, mt: 1 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
          
          {loadingUsers ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <Typography>Loading available users...</Typography>
            </Box>
          ) : filteredAvailableUsers.length === 0 ? (
            <Box sx={{ textAlign: 'center', p: 3 }}>
              <Typography color="text.secondary">
                {searchTerm ? 'No users found matching your search' : 'No available users for this shift'}
              </Typography>
            </Box>
          ) : (
            <List sx={{ maxHeight: 400, overflow: 'auto' }}>
              {filteredAvailableUsers.map(user => (
                <ListItem
                  key={user.id}
                  button
                  onClick={() => handleAddUser(user.id, user.username)}
                  sx={{
                    borderRadius: 1,
                    mb: 0.5,
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  }}
                >
                  <ListItemAvatar>
                    <Avatar>
                      <PersonIcon />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={user.username}
                    secondary={user.email}
                  />
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddUserDialogOpen(false)}>
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CoordinatorShiftGrid;