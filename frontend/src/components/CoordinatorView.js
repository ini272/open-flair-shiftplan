import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
  TextField,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Collapse,
  Divider,
  useTheme,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import AssignmentIcon from '@mui/icons-material/Assignment';
import PeopleIcon from '@mui/icons-material/People';
import ScheduleIcon from '@mui/icons-material/Schedule';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import GroupIcon from '@mui/icons-material/Group';
import PersonIcon from '@mui/icons-material/Person';
import BlockIcon from '@mui/icons-material/Block';
import CoordinatorShiftGrid from './CoordinatorShiftGrid';
import { shiftService, userService } from '../services/api';
import { translations } from '../utils/translations';

const StatsCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: theme.shadows[4],
  },
}));

const GenerateButton = styled(Button)(({ theme }) => ({
  padding: theme.spacing(1.5, 3),
  fontSize: '1rem',
  fontWeight: 'bold',
}));

const UserListItem = styled(ListItem)(({ theme }) => ({
  borderRadius: theme.spacing(1),
  marginBottom: theme.spacing(0.5),
  flexDirection: 'column',
  alignItems: 'stretch',
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
  },
}));

const ShiftChip = styled(Chip)(({ theme }) => ({
  margin: theme.spacing(0.25),
  fontSize: '0.7rem',
  height: '24px',
}));

const DRAWER_WIDTH = 380; // Increased width for more content

const CoordinatorView = ({ shifts, users }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentAssignments, setCurrentAssignments] = useState(null);
  const [error, setError] = useState(null);
  const [lastGenerated, setLastGenerated] = useState(null);
  const [maxShiftsPerUser, setMaxShiftsPerUser] = useState(10);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedUsers, setExpandedUsers] = useState(new Set());
  const [userOptOuts, setUserOptOuts] = useState({});
  
  const theme = useTheme();

  useEffect(() => {
    const loadCurrentAssignments = async () => {
      try {
        console.log('Loading current assignments...');
        const response = await shiftService.getCurrentAssignments();
        
        if (response.data.assignments && response.data.assignments.length > 0) {
          console.log('Found existing assignments:', response.data.assignments.length);
          setCurrentAssignments(response.data.assignments);
        } else {
          console.log('No existing assignments found');
        }
      } catch (error) {
        console.log('No existing assignments or error loading:', error.message);
      }
    };
    
    loadCurrentAssignments();
  }, []);

  // Load opt-outs for users when drawer opens
  useEffect(() => {
    if (drawerOpen && users && users.length > 0) {
      const loadOptOuts = async () => {
        const optOutPromises = users.map(async (user) => {
          try {
            const response = await shiftService.getUserOptOuts(user.id);
            return { userId: user.id, optOuts: response.data };
          } catch (error) {
            console.log(`Failed to load opt-outs for user ${user.id}:`, error);
            return { userId: user.id, optOuts: [] };
          }
        });

        const results = await Promise.all(optOutPromises);
        const optOutMap = {};
        results.forEach(({ userId, optOuts }) => {
          optOutMap[userId] = optOuts;
        });
        setUserOptOuts(optOutMap);
      };

      loadOptOuts();
    }
  }, [drawerOpen, users]);

  // Calculate user assignment statistics
  const userStats = React.useMemo(() => {
    if (!currentAssignments || !users) return [];
    
    const userShiftCounts = {};
    
    // Initialize all users with 0 shifts
    users.forEach(user => {
      userShiftCounts[user.id] = {
        id: user.id,
        username: user.username,
        email: user.email,
        group: user.group, // Assuming this exists in user data
        shiftCount: 0,
        shifts: []
      };
    });
    
    // Count assignments
    currentAssignments.forEach(assignment => {
      if (userShiftCounts[assignment.user_id]) {
        userShiftCounts[assignment.user_id].shiftCount++;
        userShiftCounts[assignment.user_id].shifts.push({
          id: assignment.shift_id,
          title: assignment.shift_title,
          assignedVia: assignment.assigned_via,
          groupName: assignment.group_name
        });
      }
    });
    
    // Convert to array and sort by shift count (descending)
    return Object.values(userShiftCounts).sort((a, b) => b.shiftCount - a.shiftCount);
  }, [currentAssignments, users]);

  // Calculate current statistics
  const stats = React.useMemo(() => {
    const totalShifts = shifts.length;
    const totalUsers = users.length;
    
    const shiftsToAnalyze = currentAssignments ? 
      shifts.map(shift => {
        const shiftAssignments = currentAssignments.filter(a => a.shift_id === shift.id);
        return {
          ...shift,
          users: shiftAssignments.map(a => ({ id: a.user_id, username: a.username }))
        };
      }) : shifts;
    
    const assignedShifts = shiftsToAnalyze.filter(shift => 
      shift.users && shift.users.length > 0
    ).length;
    
    const totalAssignments = shiftsToAnalyze.reduce((sum, shift) => 
      sum + (shift.users ? shift.users.length : 0), 0
    );
    
    const coveragePercentage = totalShifts > 0 ? 
      Math.round((assignedShifts / totalShifts) * 100) : 0;
    
    const underStaffedShifts = shiftsToAnalyze.filter(shift => 
      shift.capacity && shift.users && shift.users.length < shift.capacity
    ).length;
    
    return {
      totalShifts,
      totalUsers,
      assignedShifts,
      totalAssignments,
      coveragePercentage,
      underStaffedShifts
    };
  }, [shifts, users, currentAssignments]);

  const handleGeneratePlan = async () => {
    setIsGenerating(true);
    setError(null);

    try {
      console.log('Starting plan generation with max shifts per user:', maxShiftsPerUser);
      
      const response = await shiftService.generatePlan(maxShiftsPerUser);
      console.log('API response:', response);
      
      setCurrentAssignments(response.data.assignments);
      setLastGenerated(new Date());
      console.log('Plan generated successfully');
    } catch (err) {
      console.error('Detailed error:', err);
      setError(`${translations.coordinator.planGenerationFailed}: ${err.message || 'Unknown error'}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleResetAllAssignments = async () => {
    try {
      console.log('Clearing all assignments...');
      const response = await shiftService.clearAllAssignments();
      console.log('Assignments cleared:', response.data);
      
      setCurrentAssignments(null);
      setLastGenerated(null);
      setError(null);
      
      console.log('All assignments reset successfully');
    } catch (err) {
      console.error('Error clearing assignments:', err);
      setError(`Failed to reset assignments: ${err.message || 'Unknown error'}`);
    }
  };

  const toggleDrawer = () => {
    setDrawerOpen(!drawerOpen);
  };

  const toggleUserExpanded = (userId) => {
    const newExpanded = new Set(expandedUsers);
    if (newExpanded.has(userId)) {
      newExpanded.delete(userId);
    } else {
      newExpanded.add(userId);
    }
    setExpandedUsers(newExpanded);
  };

  const formatShiftTime = (shift) => {
    const shiftData = shifts.find(s => s.id === shift.id);
    if (!shiftData) return '';
    
    const startTime = new Date(shiftData.start_time);
    const endTime = new Date(shiftData.end_time);
    
    return `${startTime.toLocaleDateString('de-DE', { 
      month: 'short', 
      day: 'numeric' 
    })} ${startTime.toLocaleTimeString('de-DE', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })}-${endTime.toLocaleTimeString('de-DE', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })}`;
  };

  const renderUserList = () => (
    <Box sx={{ width: DRAWER_WIDTH, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom>
          User Assignments
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {userStats.length} users • {stats.totalAssignments} total assignments
        </Typography>
      </Box>
      
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <List sx={{ p: 1 }}>
          {userStats.map((user) => {
            const isExpanded = expandedUsers.has(user.id);
            const userOptOutList = userOptOuts[user.id] || [];
            
            return (
              <UserListItem key={user.id}>
                {/* Main user info */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', py: 1 }}>
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Typography variant="subtitle2">
                        {user.username}
                      </Typography>
                      {user.group ? (
                        <Chip 
                          icon={<GroupIcon />}
                          label={user.group.name || 'Team'}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: '0.7rem' }}
                        />
                      ) : (
                        <Chip 
                          icon={<PersonIcon />}
                          label="Individual"
                          size="small"
                          variant="outlined"
                          color="secondary"
                          sx={{ fontSize: '0.7rem' }}
                        />
                      )}
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {user.email}
                    </Typography>
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip 
                      label={user.shiftCount} 
                      size="small" 
                      color={user.shiftCount >= maxShiftsPerUser ? 'error' : user.shiftCount > 0 ? 'primary' : 'default'}
                    />
                    {(user.shifts.length > 0 || userOptOutList.length > 0) && (
                      <IconButton 
                        size="small" 
                        onClick={() => toggleUserExpanded(user.id)}
                      >
                        {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    )}
                  </Box>
                </Box>

                {/* Expandable content */}
                <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                  <Box sx={{ pl: 1, pr: 1, pb: 1 }}>
                    {/* Assigned Shifts */}
                    {user.shifts.length > 0 && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                          Assigned Shifts ({user.shifts.length})
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          {user.shifts.map((shift) => (
                            <Box key={shift.id} sx={{ mb: 0.5 }}>
                              <ShiftChip
                                label={shift.title}
                                variant="filled"
                                color={shift.assignedVia === 'group' ? 'secondary' : 'primary'}
                                size="small"
                              />
                              <Typography variant="caption" color="text.secondary" sx={{ ml: 1, display: 'block' }}>
                                {formatShiftTime(shift)}
                                {shift.assignedVia === 'group' && shift.groupName && (
                                  <span> • via {shift.groupName}</span>
                                )}
                              </Typography>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    )}

                    {/* Opt-outs */}
                    {userOptOutList.length > 0 && (
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                          Opt-outs ({userOptOutList.length})
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          {userOptOutList.map((optOutShift) => (
                            <Box key={optOutShift.id} sx={{ mb: 0.5 }}>
                              <ShiftChip
                                icon={<BlockIcon />}
                                label={optOutShift.title}
                                variant="outlined"
                                color="error"
                                size="small"
                              />
                              <Typography variant="caption" color="text.secondary" sx={{ ml: 1, display: 'block' }}>
                                {formatShiftTime(optOutShift)}
                              </Typography>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    )}

                    {/* Show message if no shifts or opt-outs */}
                    {user.shifts.length === 0 && userOptOutList.length === 0 && (
                      <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                        No assignments or opt-outs
                      </Typography>
                    )}
                  </Box>
                </Collapse>

                {user.shifts.length > 0 && !isExpanded && (
                  <Box sx={{ mt: 0.5 }}>
                    {user.shifts.slice(0, 2).map((shift) => (
                      <ShiftChip
                        key={shift.id}
                        label={shift.title}
                        size="small"
                        variant="outlined"
                        color={shift.assignedVia === 'group' ? 'secondary' : 'primary'}
                        sx={{ mr: 0.5, mb: 0.5 }}
                      />
                    ))}
                    {user.shifts.length > 2 && (
                      <Typography variant="caption" color="text.secondary">
                        +{user.shifts.length - 2} more
                      </Typography>
                    )}
                  </Box>
                )}
              </UserListItem>
            );
          })}
        </List>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Main Content */}
      <Box sx={{ 
        flex: 1, 
        p: 3, 
        transition: theme.transitions.create('margin', {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.leavingScreen,
        }),
        marginRight: drawerOpen ? `${DRAWER_WIDTH}px` : 0,
      }}>
        <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
          {translations.coordinator.dashboard}
        </Typography>

        {/* Statistics Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <StatsCard>
              <CardContent sx={{ textAlign: 'center' }}>
                <ScheduleIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                <Typography variant="h4" component="div">
                  {stats.totalShifts}
                </Typography>
                <Typography color="text.secondary">
                  {translations.coordinator.totalShifts}
                </Typography>
              </CardContent>
            </StatsCard>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <StatsCard>
              <CardContent sx={{ textAlign: 'center' }}>
                <PeopleIcon sx={{ fontSize: 40, color: 'secondary.main', mb: 1 }} />
                <Typography variant="h4" component="div">
                  {stats.totalUsers}
                </Typography>
                <Typography color="text.secondary">
                  {translations.coordinator.availableUsers}
                </Typography>
              </CardContent>
            </StatsCard>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <StatsCard>
              <CardContent sx={{ textAlign: 'center' }}>
                <AssignmentIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                <Typography variant="h4" component="div">
                  {stats.coveragePercentage}%
                </Typography>
                <Typography color="text.secondary">
                  {translations.coordinator.shiftCoverage}
                </Typography>
              </CardContent>
            </StatsCard>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <StatsCard>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" component="div" color="warning.main">
                  {stats.underStaffedShifts}
                </Typography>
                <Typography color="text.secondary">
                  {translations.coordinator.understaffedShifts}
                </Typography>
              </CardContent>
            </StatsCard>
          </Grid>
        </Grid>

        {/* Shift Assignments Section */}
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
            <Box>
              <Typography variant="h5" gutterBottom>
                {translations.coordinator.shiftAssignments}
              </Typography>
              {lastGenerated && (
                <Typography variant="body2" color="text.secondary">
                  {translations.coordinator.lastGenerated}: {lastGenerated.toLocaleString()}
                </Typography>
              )}
            </Box>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'flex-end' }}>
              {/* Max Shifts Input */}
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                <TextField
                  type="number"
                  label="Max Shifts per User"
                  value={maxShiftsPerUser}
                  onChange={(e) => setMaxShiftsPerUser(parseInt(e.target.value) || 10)}
                  inputProps={{ min: 1, max: 20 }}
                  sx={{ width: 180 }}
                  size="small"
                />
              </Box>
              {/* Action Buttons */}
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={handleResetAllAssignments}
                  disabled={isGenerating || !currentAssignments}
                >
                  Reset All
                </Button>
                <GenerateButton
                  variant="contained"
                  startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                  onClick={handleGeneratePlan}
                  disabled={isGenerating}
                >
                  {isGenerating ? translations.coordinator.generating : translations.coordinator.generatePlan}
                </GenerateButton>
              </Box>
            </Box>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {currentAssignments && (
            <Alert severity="success" sx={{ mb: 3 }}>
              {translations.coordinator.assignmentsGenerated} {currentAssignments.length} {translations.coordinator.shiftAssignments.toLowerCase()}
            </Alert>
          )}
          
          <CoordinatorShiftGrid 
            shifts={shifts} 
            generatedAssignments={currentAssignments}
          />
        </Paper>
      </Box>

      {/* User List Toggle Button */}
      <IconButton
        onClick={toggleDrawer}
        sx={{
          position: 'fixed',
          top: '50%',
          right: drawerOpen ? DRAWER_WIDTH : 0,
          transform: 'translateY(-50%)',
          zIndex: 1201,
          backgroundColor: 'background.paper',
          boxShadow: 2,
          '&:hover': {
            backgroundColor: 'background.paper',
          },
        }}
      >
        {drawerOpen ? <ChevronRightIcon /> : <ChevronLeftIcon />}
      </IconButton>

      {/* User List Drawer */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={toggleDrawer}
        variant="persistent"
        sx={{
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
          },
        }}
      >
        {renderUserList()}
      </Drawer>
    </Box>
  );
};

export default CoordinatorView;