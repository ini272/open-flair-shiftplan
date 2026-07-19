import React from 'react';
import {
  Alert,
  Button,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import RefreshIcon from '@mui/icons-material/Refresh';
import CoordinatorPersonView from './CoordinatorPersonView';
import { translations } from '../utils/translations';

const ParticipantAssignments = ({
  plan,
  isLoading,
  error,
  onRefresh,
  shifts,
  selectedViewOption,
  optedOutShifts,
}) => {

  if (isLoading) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center', borderRadius: 3 }}>
        <CircularProgress size={28} />
      </Paper>
    );
  }

  if (error) {
    return <Alert severity="error">{translations.shifts.assignmentsLoadFailed}</Alert>;
  }

  if (!plan.is_released) {
    return (
      <Paper sx={{ p: { xs: 3, sm: 4 }, textAlign: 'center', borderRadius: 3 }}>
        <Stack spacing={1.25} sx={{ alignItems: 'center' }}>
          <AssignmentTurnedInIcon color="disabled" sx={{ fontSize: 38 }} />
          <Typography variant="h6">
            {translations.shifts.assignmentsPendingReleaseTitle}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {translations.shifts.assignmentsPendingReleaseBody}
          </Typography>
          <Button size="small" startIcon={<RefreshIcon />} onClick={onRefresh}>
            {translations.shifts.refreshAssignments}
          </Button>
        </Stack>
      </Paper>
    );
  }

  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: { xs: 1.5, sm: 2 }, borderRadius: 3 }}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1}
          alignItems={{ sm: 'center' }}
          justifyContent="space-between"
        >
          <Typography variant="body2" color="text.secondary">
            {translations.shifts.assignmentsCurrentPlanHint}
          </Typography>
          <Button size="small" startIcon={<RefreshIcon />} onClick={onRefresh}>
            {translations.shifts.refreshAssignments}
          </Button>
        </Stack>
      </Paper>

      <CoordinatorPersonView
        shifts={shifts}
        selectedViewOption={selectedViewOption}
        generatedAssignments={plan.assignments}
        userOptOuts={selectedViewOption?.type === 'user'
          ? { [selectedViewOption.id]: optedOutShifts }
          : {}}
        groupOptOuts={selectedViewOption?.type === 'group'
          ? { [selectedViewOption.id]: optedOutShifts }
          : {}}
        loadingSelectionContext={false}
        assignmentsAreScopedToSelectedView
      />
    </Stack>
  );
};

export default ParticipantAssignments;
