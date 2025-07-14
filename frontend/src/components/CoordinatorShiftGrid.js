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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  TextField,
  InputAdornment,
  Divider,
  Tooltip
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PersonIcon from '@mui/icons-material/Person';
import GroupIcon from '@mui/icons-material/Group';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import { shiftService, groupService } from '../services/api';
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

const CoordinatorShiftGrid = ({ shifts, generatedAssignments, onAssignmentsChange }) => {
  const [addUserDialogOpen, setAddUserDialogOpen] = useState(false);
  const [selectedShift, setSelectedShift] = useState(null);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [availableGroups, setAvailableGroups] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  // Merge shifts with generated assignments
  const shiftsWithAssignments = useMemo(() => {
    if (!generatedAssignments) return shifts;
    
    return shifts.map(shift => {
      const shiftAssignments = generatedAssignments.filter(
        assignment => assignment.shift_id === shift.id
      );
      
      // Group assignments by type
      const userAssignments = shiftAssignments.filter(a => a.assigned_via === 'individual');
      const groupAssignments = shiftAssignments.filter(a => a.assigned_via === 'group');
      
      // Create unique group list
      const uniqueGroups = {};
      groupAssignments.forEach(assignment => {
        if (!uniqueGroups[assignment.group_name]) {
          uniqueGroups[assignment.group_name] = {
            name: assignment.group_name,
            users: []
          };
        }
        uniqueGroups[assignment.group_name].users.push({
          id: assignment.user_id,
          username: assignment.username
        });
      });
      
      const assignedUsers = userAssignments.map(assignment => ({
        id: assignment.user_id,
        username: assignment.username,
        assignedVia: 'individual'
      }));
      
      const assignedGroups = Object.values(uniqueGroups);
      
      return {
        ...shift,
        users: assignedUsers,
        groups: assignedGroups
      };
    });
  }, [shifts, generatedAssignments]);

  // Group shifts by date with smart sorting
  const shiftsByDate = useMemo(() => {
    const grouped = {};
    
    shiftsWithAssignments.forEach(shift => {
      const date = new Date(shift.start_time).toDateString();
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

  // Determine staffing level
  const getStaffingLevel = (shift) => {
    const currentStaff = (shift.users?.length || 0) + 
                        (shift.groups?.reduce((sum, group) => sum + group.users.length, 0) || 0);
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

  // Open add user/group dialog
  const handleOpenAddUserDialog = async (shift) => {
    setSelectedShift(shift);
    setLoading(true);
    setAddUserDialogOpen(true);
    
    try {
      // Get available users (only individual users, not group members)
      const usersResponse = await shiftService.getAvailableUsers(shift.id);
      const allUsers = usersResponse.data;
      
      // Get all groups (basic info only)
      const groupsResponse = await groupService.getGroups();
      const allGroups = groupsResponse.data;
      
      // Filter out users who are already in groups
      const individualUsers = allUsers.filter(user => !user.group_id);
      
      // Filter out groups that are already assigned to this shift
      const assignedGroupNames = shift.groups?.map(g => g.name) || [];
      const availableGroupsBasic = allGroups.filter(group => 
        !assignedGroupNames.includes(group.name) && group.is_active
      );
      
      // Fetch detailed info for each available group to get user count
      const availableGroupsWithUsers = await Promise.all(
        availableGroupsBasic.map(async (group) => {
          try {
            const groupDetailResponse = await groupService.getGroup(group.id);
            return groupDetailResponse.data;
          } catch (error) {
            console.error(`Error fetching details for group ${group.id}:`, error);
            return { ...group, users: [] }; // Fallback
          }
        })
      );
      
      // Only show groups that have members
      const groupsWithMembers = availableGroupsWithUsers.filter(group => 
        group.users && group.users.length > 0
      );
      
      setAvailableUsers(individualUsers);
      setAvailableGroups(groupsWithMembers);
    } catch (error) {
      console.error('Error loading available users/groups:', error);
    } finally {
      setLoading(false);
    }
  };

  // Add individual user to shift
  const handleAddUser = async (userId, username) => {
    try {
      await shiftService.addUserToShift({
        shift_id: selectedShift.id,
        user_id: userId
      });
      
      // Refresh assignments if callback provided
      if (onAssignmentsChange) {
        onAssignmentsChange();
      }
      
      setAddUserDialogOpen(false);
      setSearchTerm('');
    } catch (error) {
      console.error('Error adding user to shift:', error);
    }
  };

  // Add group to shift
  const handleAddGroup = async (groupId, groupName) => {
    try {
      await shiftService.addGroupToShift({
        shift_id: selectedShift.id,
        group_id: groupId
      });
      
      // Refresh assignments if callback provided
      if (onAssignmentsChange) {
        onAssignmentsChange();
      }
      
      setAddUserDialogOpen(false);
      setSearchTerm('');
    } catch (error) {
      console.error('Error adding group to shift:', error);
    }
  };

  // Remove user from shift
  const handleRemoveUser = async (shift, userId) => {
    try {
      await shiftService.removeUserFromShift(shift.id, userId);
      
      if (onAssignmentsChange) {
        onAssignmentsChange();
      }
    } catch (error) {
      console.error('Error removing user from shift:', error);
    }
  };

  // Remove group from shift
  const handleRemoveGroup = async (shift, groupName) => {
    try {
      // Find the group ID by name
      const groupsResponse = await groupService.getGroups();
      const group = groupsResponse.data.find(g => g.name === groupName);
      
      if (group) {
        await shiftService.removeGroupFromShift(shift.id, group.id);
        
        if (onAssignmentsChange) {
          onAssignmentsChange();
        }
      }
    } catch (error) {
      console.error('Error removing group from shift:', error);
    }
  };

  // Filter users and groups based on search term
  const filteredUsers = availableUsers.filter(user =>
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredGroups = availableGroups.filter(group =>
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
                const currentStaff = (shift.users?.length || 0) + 
                                   (shift.groups?.reduce((sum, group) => sum + group.users.length, 0) || 0);
                
                return (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={shift.id}>
                    <ShiftCard staffingLevel={staffingLevel}>
                      <CardContent sx={{ p: 2 }}>
                        {/* Shift Header */}
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', lineHeight: 1.2 }}>
                            {shift.title}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                            <Chip 
                              size="small" 
                              label={getStaffingText(staffingLevel)}
                              color={getStaffingColor(staffingLevel)}
                            />
                            <IconButton 
                              size="small" 
                              onClick={() => handleOpenAddUserDialog(shift)}
                              sx={{
                                width: 24,
                                height: 24,
                                backgroundColor: 'primary.main',
                                color: 'white',
                                '&:hover': {
                                  backgroundColor: 'primary.dark',
                                }
                              }}
                            >
                              <AddIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        </Box>
                        
                        {/* Time */}
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
                        </Typography>
                        
                        {/* Capacity */}
                        <Typography variant="body2" sx={{ mb: 2 }}>
                          <strong>{translations.shifts.capacity}:</strong> {currentStaff}/{shift.capacity || '∞'}
                        </Typography>
                        
                        {/* Assigned Groups - Show Members */}
                        {shift.groups && shift.groups.length > 0 && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                              Teams:
                            </Typography>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap">
                              {shift.groups.map(group => (
                                <UserChip
                                  key={`group-${group.name}`}
                                  avatar={<Avatar sx={{ backgroundColor: 'secondary.main' }}><GroupIcon fontSize="small" /></Avatar>}
                                  label={group.users.map(user => user.username).join(', ')}
                                  size="small"
                                  color="secondary"
                                  onDelete={() => handleRemoveGroup(shift, group.name)}
                                  deleteIcon={<CloseIcon />}
                                  sx={{ 
                                    maxWidth: '300px',
                                    '& .MuiChip-label': {
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap'
                                    }
                                  }}
                                />
                              ))}
                            </Stack>
                          </Box>
                        )}
                        
                        {/* Assigned Individual Users */}
                        {shift.users && shift.users.length > 0 && (
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                              Einzelpersonen:
                            </Typography>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap">
                              {shift.users.slice(0, 3).map(user => (
                                <UserChip
                                  key={user.id}
                                  avatar={<Avatar><PersonIcon fontSize="small" /></Avatar>}
                                  label={user.username}
                                  size="small"
                                  variant="outlined"
                                  onDelete={() => handleRemoveUser(shift, user.id)}
                                  deleteIcon={<CloseIcon />}
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
                        )}
                        
                        {/* No assignments */}
                        {currentStaff === 0 && (
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

      {/* Add User/Group Dialog */}
      <Dialog 
        open={addUserDialogOpen} 
        onClose={() => setAddUserDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Benutzer/Gruppe zu Schicht hinzufügen
          {selectedShift && (
            <Typography variant="subtitle2" color="text.secondary">
              {selectedShift.title} - {formatTime(selectedShift.start_time)} bis {formatTime(selectedShift.end_time)}
            </Typography>
          )}
        </DialogTitle>
        
        <DialogContent>
          {/* Search Field */}
          <TextField
            fullWidth
            placeholder="Suche nach Benutzern oder Gruppen..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
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
              <Typography>Lade verfügbare Benutzer und Gruppen...</Typography>
            </Box>
          ) : (
            <List sx={{ maxHeight: 400, overflow: 'auto' }}>
              {/* Available Groups */}
              {filteredGroups.length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ px: 2, py: 1, backgroundColor: 'grey.100' }}>
                    Verfügbare Gruppen
                  </Typography>
                  {filteredGroups.map(group => (
                    <ListItem 
                      key={`group-${group.id}`}
                      button 
                      onClick={() => handleAddGroup(group.id, group.name)}
                      sx={{ 
                        '&:hover': { backgroundColor: 'action.hover' },
                        borderRadius: 1,
                        mx: 1,
                        mb: 0.5
                      }}
                    >
                      <ListItemAvatar>
                        <Avatar sx={{ backgroundColor: 'secondary.main' }}>
                          <GroupIcon />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText 
                        primary={`${group.name} (${group.users?.map(u => u.username).join(', ') || 'No members'})`}
                        secondary={`${group.users?.length || 0} Mitglieder`}
                      />
                    </ListItem>
                  ))}
                  {filteredUsers.length > 0 && <Divider sx={{ my: 1 }} />}
                </>
              )}
              
              {/* Available Individual Users */}
              {filteredUsers.length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ px: 2, py: 1, backgroundColor: 'grey.100' }}>
                    Verfügbare Einzelpersonen
                  </Typography>
                  {filteredUsers.map(user => (
                    <ListItem 
                      key={user.id}
                      button 
                      onClick={() => handleAddUser(user.id, user.username)}
                      sx={{ 
                        '&:hover': { backgroundColor: 'action.hover' },
                        borderRadius: 1,
                        mx: 1,
                        mb: 0.5
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
                </>
              )}
              
              {/* No results */}
              {filteredUsers.length === 0 && filteredGroups.length === 0 && !loading && (
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  <Typography color="text.secondary">
                    {searchTerm ? 'Keine Ergebnisse gefunden' : 'Keine verfügbaren Benutzer oder Gruppen'}
                  </Typography>
                </Box>
              )}
            </List>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setAddUserDialogOpen(false)}>
            Abbrechen
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CoordinatorShiftGrid;