import React, { useState } from 'react';
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
  Checkbox
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import AssignmentIcon from '@mui/icons-material/Assignment';
import PeopleIcon from '@mui/icons-material/People';
import ScheduleIcon from '@mui/icons-material/Schedule';
import CoordinatorShiftGrid from './CoordinatorShiftGrid';
import { shiftService } from '../services/api';

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
  const [clearExisting, setClearExisting] = useState(true); // Default to true for better UX
  const [useGroups, setUseGroups] = useState(true);

  // Calculate current statistics
  const stats = React.useMemo(() => {
    const totalShifts = shifts.length;
    const totalUsers = users.length;
    
    // Use current assignments if available, otherwise use existing shift data
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
      console.log('Starting plan generation with options:', { clearExisting, useGroups });
      
      const response = await shiftService.generatePlan(clearExisting, useGroups);
      console.log('API response:', response);
      
      setCurrentAssignments(response.data.assignments);
      setLastGenerated(new Date());
      console.log('Plan generated successfully');
    } catch (err) {
      console.error('Detailed error:', err);
      setError(`Failed to generate shift plan: ${err.message || 'Unknown error'}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        Coordinator Dashboard
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
                Total Shifts
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
                Available Users
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
                Shift Coverage
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
                Under-staffed Shifts
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
              Shift Assignments
            </Typography>
            {lastGenerated && (
              <Typography variant="body2" color="text.secondary">
                Last generated: {lastGenerated.toLocaleString()}
              </Typography>
            )}
          </Box>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'flex-end' }}>
            {/* Options */}
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={clearExisting}
                    onChange={(e) => setClearExisting(e.target.checked)}
                    color="primary"
                  />
                }
                label="Clear existing assignments"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={useGroups}
                    onChange={(e) => setUseGroups(e.target.checked)}
                    color="primary"
                  />
                }
                label="Use group assignments"
              />
            </Box>
            
            {/* Generate Button */}
            <GenerateButton
              variant="contained"
              startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
              onClick={handleGeneratePlan}
              disabled={isGenerating}
            >
              {isGenerating ? 'Generating...' : 'Generate Plan'}
            </GenerateButton>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {currentAssignments && (
          <Alert severity="success" sx={{ mb: 3 }}>
            Successfully generated {currentAssignments.length} assignments
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