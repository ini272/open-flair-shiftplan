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
  FormControlLabel,
  Checkbox,
  TextField
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import AssignmentIcon from '@mui/icons-material/Assignment';
import PeopleIcon from '@mui/icons-material/People';
import ScheduleIcon from '@mui/icons-material/Schedule';
import CoordinatorShiftGrid from './CoordinatorShiftGrid';
import { shiftService } from '../services/api';
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

const CoordinatorView = ({ shifts, users }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentAssignments, setCurrentAssignments] = useState(null);
  const [error, setError] = useState(null);
  const [lastGenerated, setLastGenerated] = useState(null);
  const [maxShiftsPerUser, setMaxShiftsPerUser] = useState(10);

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
        // This is fine - coordinator hasn't generated a plan yet
      }
    };
    
    loadCurrentAssignments();
  }, []); // Empty dependency array - only run on mount

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
      
      // Clear the local state
      setCurrentAssignments(null);
      setLastGenerated(null);
      setError(null);
      
      // Show success (you could add a success state if you want)
      console.log('All assignments reset successfully');
    } catch (err) {
      console.error('Error clearing assignments:', err);
      setError(`Failed to reset assignments: ${err.message || 'Unknown error'}`);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
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
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <TextField
                type="number"
                label="Max Shifts per User (Festival)"
                value={maxShiftsPerUser}
                onChange={(e) => setMaxShiftsPerUser(parseInt(e.target.value) || 10)}
                inputProps={{ min: 1, max: 20 }}
                sx={{ width: 220 }}
                size="small"
              />
            </Box>
            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 1 }}>
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
  );
};

export default CoordinatorView;