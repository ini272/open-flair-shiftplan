import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, 
  Checkbox,
  Container, 
  Paper, 
  Typography, 
  Tabs, 
  Tab, 
  TextField, 
  Button, 
  Alert,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Autocomplete,
  MenuItem,
  Select,
  InputLabel,
  FormControl as MuiFormControl
} from '@mui/material';
import { authService, userService, groupService } from '../services/api';
import Logo from '../components/Logo';
import { translations } from '../utils/translations';
import GroupIcon from '@mui/icons-material/Group';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_GROUP_SIZE = 3;

const isValidEmail = (value) => EMAIL_REGEX.test(value.trim());

const getApiErrorDetail = (error) => {
  const detail = error?.response?.data?.detail;
  return typeof detail === 'string' ? detail.trim() : '';
};

const getAccountErrorMessage = (error, fallback, options = {}) => {
  const detail = getApiErrorDetail(error);
  const fallbackMessage = fallback || translations.account.accountLookupFailed;
  const { groupName } = options;

  if (!detail) {
    if (error?.message && !error.message.startsWith('Request failed with status code')) {
      return error.message;
    }
    return fallbackMessage;
  }

  const detailMap = {
    'Email already registered': translations.account.emailAlreadyRegistered,
    'Username already taken': translations.account.usernameAlreadyTaken,
    'Group with this name already exists': translations.account.groupAlreadyExists,
    'User not found': translations.account.userNotFound,
    'Failed to add user to group': translations.account.groupJoinFailed,
    'Coordinator accounts cannot join groups': translations.account.coordinatorCannotJoinGroups,
    'Users under 16 cannot join groups': translations.account.under16GroupHint,
  };

  if (detailMap[detail]) {
    return detailMap[detail];
  }

  if (detail.startsWith('Group is full')) {
    return `Die Gruppe "${groupName}" ist voll (maximal ${MAX_GROUP_SIZE} Mitglieder). Bitte wähle einen anderen Gruppennamen oder arbeite alleine.`;
  }

  return detail;
};

// Tab panel component
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`account-tabpanel-${index}`}
      aria-labelledby={`account-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const AccountAccessPage = () => {
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  
  // New user state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [isUnder16, setIsUnder16] = useState(false);
  const [workPreference, setWorkPreference] = useState('alone');
  const [groupName, setGroupName] = useState('');
  const [newUserError, setNewUserError] = useState('');
  const [newUserLoading, setNewUserLoading] = useState(false);
  const [newUserFieldErrors, setNewUserFieldErrors] = useState({
    username: '',
    email: '',
    group: '',
  });
  
  // Returning user state
  const [returningEmail, setReturningEmail] = useState('');
  const [returningError, setReturningError] = useState('');
  const [returningLoading, setReturningLoading] = useState(false);
  const [returningEmailError, setReturningEmailError] = useState('');

  const [existingGroups, setExistingGroups] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [authRole, setAuthRole] = useState(null);
  const isCoordinatorAccess = authRole === 'coordinator';
  const trimmedGroupName = groupName.trim();
  const selectedExistingGroup = existingGroups.find((group) => group.name === trimmedGroupName) || null;

  useEffect(() => {
    const loadAuthRole = async () => {
      try {
        const response = await authService.checkAuth();
        setAuthRole(response.data.role || null);
      } catch (error) {
        console.warn('Could not determine access role:', error);
        setAuthRole(null);
      }
    };

    loadAuthRole();
  }, []);

  useEffect(() => {
    const loadExistingGroups = async () => {
      if (isCoordinatorAccess) {
        setExistingGroups([]);
        setLoadingGroups(false);
        return;
      }

      try {
        setLoadingGroups(true);
        const response = await groupService.getGroups();
        const basicGroups = response.data || [];
        
        // Fetch detailed info for each group to get members
        const groupsWithMembers = await Promise.all(
          basicGroups.map(async (group) => {
            try {
              const groupDetailResponse = await groupService.getGroup(group.id);
              return groupDetailResponse.data;
            } catch (error) {
              console.error(`Error fetching details for group ${group.id}:`, error);
              return { ...group, users: [] }; // Fallback
            }
          })
        );
        
        setExistingGroups(groupsWithMembers);
      } catch (error) {
        console.warn('Could not load existing groups:', error);
        // Not critical - user can still type manually
      } finally {
        setLoadingGroups(false);
      }
    };
    
    loadExistingGroups();
  }, [isCoordinatorAccess]);

  useEffect(() => {
    if (isUnder16 && workPreference === 'group') {
      setWorkPreference('alone');
    }
  }, [isUnder16, workPreference]);

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Handle new user submission
  const handleNewUserSubmit = async (e) => {
    e.preventDefault();
    setNewUserError('');
    setNewUserFieldErrors({
      username: '',
      email: '',
      group: '',
    });

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    const nextFieldErrors = {
      username: '',
      email: '',
      group: '',
    };

    if (!trimmedName) {
      nextFieldErrors.username = translations.account.usernameRequired;
    }

    if (!trimmedEmail) {
      nextFieldErrors.email = translations.account.emailRequired;
    } else if (!isValidEmail(trimmedEmail)) {
      nextFieldErrors.email = translations.account.emailInvalid;
    }

    if (workPreference === 'group' && !trimmedGroupName) {
      nextFieldErrors.group = translations.account.groupRequired;
    }

    if (nextFieldErrors.username || nextFieldErrors.email || nextFieldErrors.group) {
      setNewUserFieldErrors(nextFieldErrors);
      return;
    }

    setNewUserLoading(true);
    
    try {
      
      const wantsGroup = !isCoordinatorAccess && !isUnder16 && workPreference === 'group';

      // If working in a group, check if group is full BEFORE creating user
      if (wantsGroup) {
        try {
          const groupsResponse = await groupService.getGroups();
          const existingGroup = groupsResponse.data.find(g => g.name === trimmedGroupName);
          
          if (existingGroup) {
            // Check if group is full by getting group details
            const groupDetails = await groupService.getGroup(existingGroup.id);
            const currentSize = groupDetails.data.users ? groupDetails.data.users.length : 0;
            const maxSize = MAX_GROUP_SIZE;
            
            if (currentSize >= maxSize) {
              throw new Error(`Die Gruppe "${trimmedGroupName}" ist voll (maximal ${maxSize} Mitglieder). Bitte wähle einen anderen Gruppennamen oder arbeite alleine.`);
            }
          }
        } catch (groupErr) {
            if (groupErr.message && groupErr.message.includes('voll')) {
              throw groupErr; // Re-throw our custom error
            }
          // If it's just a network error checking groups, continue
          console.warn('Could not check group status:', groupErr);
        }
      }
      
      // Now create the user
      const userResponse = await userService.createUser({
        username: trimmedName,
        email: trimmedEmail,
        is_under_16: isUnder16,
      });

      // Store user info in localStorage
      localStorage.setItem('user_id', userResponse.data.id);
      localStorage.setItem('username', trimmedName);
      
      // If working in a group, join or create the group
      if (wantsGroup) {
        try {
          const groupsResponse = await groupService.getGroups();
          const existingGroup = groupsResponse.data.find(g => g.name === trimmedGroupName);
          
          if (existingGroup) {
            // Join existing group
            await groupService.addUserToGroup(existingGroup.id, userResponse.data.id, MAX_GROUP_SIZE);
          } else {
            // Create new group
            const newGroupResponse = await groupService.createGroup({ name: trimmedGroupName });
            await groupService.addUserToGroup(newGroupResponse.data.id, userResponse.data.id, MAX_GROUP_SIZE);
          }
        } catch (groupErr) {
          // If group joining fails, we need to clean up the user
          console.error('Group joining failed, cleaning up user:', groupErr);
          
          try {
            await userService.deleteUser(userResponse.data.id);
          } catch (cleanupErr) {
            console.error('Failed to cleanup user:', cleanupErr);
          }
          
          // Show German error message
          if (groupErr.response && groupErr.response.status === 400 && groupErr.response.data.detail) {
            throw new Error(
              getAccountErrorMessage(groupErr, translations.account.groupJoinFailed, {
                groupName: trimmedGroupName,
              })
            );
          }
          throw new Error(translations.account.groupJoinFailed);
        }
      }

      navigate('/dashboard');
      
    } catch (err) {
      if (!err?.response) {
        console.error('Error during new user setup:', err);
      }
      setNewUserError(
        getAccountErrorMessage(err, translations.account.createFailed, {
          groupName: trimmedGroupName,
        })
      );
    } finally {
      setNewUserLoading(false);
    }
  };

  // Handle returning user submission
  const handleReturningUserSubmit = async (e) => {
    e.preventDefault();
    setReturningError('');
    setReturningEmailError('');

    const trimmedEmail = returningEmail.trim();

    if (!trimmedEmail) {
      setReturningEmailError(translations.account.emailRequired);
      return;
    }

    if (!isValidEmail(trimmedEmail)) {
      setReturningEmailError(translations.account.emailInvalid);
      return;
    }

    setReturningLoading(true);
    
    try {
      
      // Look up user by email
      const response = await userService.lookupByEmail(trimmedEmail);
      const user = response.data;

      // Store user info in localStorage
      localStorage.setItem('user_id', user.id);
      localStorage.setItem('username', user.username);

      navigate('/dashboard');
    } catch (err) {
      if (!err?.response || err.response.status !== 404) {
        console.error('Error looking up user:', err);
      }
      if (err.response && err.response.status === 404) {
        setReturningError(translations.account.userNotFound);
      } else {
        setReturningError(getAccountErrorMessage(err, translations.account.lookupFailed));
      }
    } finally {
      setReturningLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Logo size="large" />
        </Box>
        
        <Paper sx={{ p: 3 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            {translations.account.accountAccess}
          </Typography>
          
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              aria-label={translations.account.accountAccessTabsLabel}
            >
              <Tab label={translations.account.newUser} id="account-tab-0" aria-controls="account-tabpanel-0" />
              <Tab label={translations.account.existingUser} id="account-tab-1" aria-controls="account-tabpanel-1" />
            </Tabs>
          </Box>
          
          {/* New User Tab */}
          <TabPanel value={tabValue} index={0}>
            <Typography variant="h6" gutterBottom>
              {translations.account.createAccount}
            </Typography>
            
            {newUserError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {newUserError}
              </Alert>
            )}

            {isCoordinatorAccess && (
              <Alert severity="info" sx={{ mb: 2 }}>
                {translations.account.coordinatorAccountInfo}
              </Alert>
            )}
            
            <Box component="form" onSubmit={handleNewUserSubmit} noValidate>
              <TextField
                label={translations.account.username}
                fullWidth
                margin="normal"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (newUserFieldErrors.username) {
                    setNewUserFieldErrors((prev) => ({ ...prev, username: '' }));
                  }
                }}
                required
                error={Boolean(newUserFieldErrors.username)}
                helperText={newUserFieldErrors.username || translations.account.nameHelper}
              />
              
              <TextField
                label={translations.account.email}
                type="text"
                fullWidth
                margin="normal"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (newUserFieldErrors.email) {
                    setNewUserFieldErrors((prev) => ({ ...prev, email: '' }));
                  }
                }}
                required
                error={Boolean(newUserFieldErrors.email)}
                helperText={newUserFieldErrors.email || translations.account.emailHelper}
                autoComplete="email"
                inputProps={{
                  inputMode: 'email',
                  autoCapitalize: 'none',
                  autoCorrect: 'off',
                }}
              />
              
              {!isCoordinatorAccess && (
                <FormControl component="fieldset" margin="normal" sx={{ width: '100%' }}>
                  <FormControlLabel
                    control={(
                      <Checkbox
                        checked={isUnder16}
                        onChange={(event) => setIsUnder16(event.target.checked)}
                      />
                    )}
                    label={translations.account.under16Label}
                    sx={{ mb: 0.5 }}
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.25 }}>
                    {translations.account.under16Helper}
                  </Typography>

                  <FormLabel component="legend">{translations.account.workPreference}</FormLabel>
                  <RadioGroup
                    value={workPreference}
                    onChange={(e) => setWorkPreference(e.target.value)}
                  >
                    <FormControlLabel
                      value="alone"
                      control={<Radio />}
                      label={translations.account.workAlone}
                    />
                    <FormControlLabel
                      value="group"
                      control={<Radio />}
                      label={translations.account.workInGroup}
                      disabled={isUnder16}
                    />
                  </RadioGroup>
                  {isUnder16 && (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      {translations.account.under16GroupHint}
                    </Alert>
                  )}
                </FormControl>
              )}
              
              {!isCoordinatorAccess && workPreference === 'group' && (
                <Box sx={{ mt: 1 }}>
                  <Alert severity="info" sx={{ mb: 1.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.25 }}>
                      {translations.account.groupInfoTitle}
                    </Typography>
                    <Typography variant="body2">
                      {translations.account.groupInfoBody}
                    </Typography>
                  </Alert>

                  <Autocomplete
                    freeSolo
                    options={existingGroups.map(group => group.name)}
                    value={groupName}
                    onChange={(event, newValue) => {
                      setGroupName(newValue || '');
                      if (newUserFieldErrors.group) {
                        setNewUserFieldErrors((prev) => ({ ...prev, group: '' }));
                      }
                    }}
                    onInputChange={(event, newInputValue) => {
                      setGroupName(newInputValue);
                      if (newUserFieldErrors.group) {
                        setNewUserFieldErrors((prev) => ({ ...prev, group: '' }));
                      }
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label={translations.account.group}
                        fullWidth
                        margin="normal"
                        required
                        error={Boolean(newUserFieldErrors.group)}
                        helperText={newUserFieldErrors.group || translations.account.groupHelper}
                        disabled={loadingGroups}
                      />
                    )}
                    renderOption={(props, option) => {
                      const group = existingGroups.find(g => g.name === option);
                      const memberNames = group?.users?.map(u => u.username).join(', ') || '';
                      const currentSize = group?.users?.length || 0;
                      const isFull = currentSize >= MAX_GROUP_SIZE;
                      
                      return (
                        <li {...props}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <GroupIcon fontSize="small" />
                            <Box>
                              <Typography variant="body2">
                                {option}
                                {memberNames && (
                                  <Typography component="span" variant="body2" color="text.secondary">
                                    {' '}({memberNames})
                                  </Typography>
                                )}
                              </Typography>
                              <Typography variant="caption" color={isFull ? "error.main" : "text.secondary"}>
                                {currentSize}/{MAX_GROUP_SIZE} {translations.account.groupCapacityLabel}
                                {isFull && ' - Voll'}
                              </Typography>
                            </Box>
                          </Box>
                        </li>
                      );
                    }}
                    noOptionsText={translations.account.noGroupsFoundCreateNew}
                    loading={loadingGroups}
                  />

                  <Box
                    sx={{
                      mt: 1.25,
                      px: 1.5,
                      py: 1.25,
                      borderRadius: 2,
                      backgroundColor: 'grey.50',
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                      {translations.account.selectedGroupMembers}
                    </Typography>
                    {selectedExistingGroup ? (
                      <>
                        <Typography variant="body2" sx={{ mb: 0.35 }}>
                          {selectedExistingGroup.users?.map((user) => user.username).join(', ') || translations.account.newGroupPreview}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {(selectedExistingGroup.users?.length || 0)}/{MAX_GROUP_SIZE} {translations.account.groupCapacityLabel}
                        </Typography>
                      </>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        {trimmedGroupName ? translations.account.newGroupPreview : translations.account.groupHelper}
                      </Typography>
                    )}
                  </Box>
                </Box>
              )}
              
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={newUserLoading}
              >
                {newUserLoading ? translations.account.creatingAccount : translations.account.createAccountButton}
              </Button>
            </Box>
          </TabPanel>
          
          {/* Returning User Tab */}
          <TabPanel value={tabValue} index={1}>
            <Typography variant="h6" gutterBottom>
              {translations.account.welcomeBack}
            </Typography>
            
            {returningError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {returningError}
              </Alert>
            )}
            
            <Box component="form" onSubmit={handleReturningUserSubmit} noValidate>
              <TextField
                label={translations.account.email}
                type="text"
                fullWidth
                margin="normal"
                value={returningEmail}
                onChange={(e) => {
                  setReturningEmail(e.target.value);
                  if (returningEmailError) {
                    setReturningEmailError('');
                  }
                }}
                required
                error={Boolean(returningEmailError)}
                helperText={returningEmailError || translations.account.returningEmailHelper}
                autoComplete="email"
                inputProps={{
                  inputMode: 'email',
                  autoCapitalize: 'none',
                  autoCorrect: 'off',
                }}
              />
              
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={returningLoading}
              >
                {returningLoading ? translations.account.searchingAccount : translations.account.continue}
              </Button>
            </Box>
          </TabPanel>
        </Paper>
        
        <Typography variant="body2" sx={{ mt: 4, textAlign: 'center', color: 'text.secondary' }}>
          {translations.festival.dates} • {translations.festival.location}
        </Typography>
      </Box>
    </Container>
  );
};

export default AccountAccessPage;
