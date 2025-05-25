import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, 
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
  Radio
} from '@mui/material';
import { userService, groupService } from '../services/api';

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
  const [workPreference, setWorkPreference] = useState('alone');
  const [groupName, setGroupName] = useState('');
  const [newUserError, setNewUserError] = useState('');
  const [newUserLoading, setNewUserLoading] = useState(false);
  
  // Returning user state
  const [returningEmail, setReturningEmail] = useState('');
  const [returningError, setReturningError] = useState('');
  const [returningLoading, setReturningLoading] = useState(false);

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Handle new user submission
  const handleNewUserSubmit = async (e) => {
    e.preventDefault();
    setNewUserError('');
    setNewUserLoading(true);
    
    console.log('Creating new user:', { name, email, workPreference, groupName });
    
    try {
      // Validate inputs
      if (!name.trim()) {
        throw new Error('Please enter your name');
      }
      
      if (!email.trim()) {
        throw new Error('Please enter your email');
      }
      
      if (workPreference === 'group' && !groupName.trim()) {
        throw new Error('Please enter a group name');
      }
      
      // Create user
      const userResponse = await userService.createUser({
        username: name,
        email: email
      });
      
      console.log('User created successfully:', userResponse.data);
      
      // Store user info in localStorage
      localStorage.setItem('user_id', userResponse.data.id);
      localStorage.setItem('username', name);
      
      // If working in a group, join or create the group
      if (workPreference === 'group') {
        try {
          // Try to find if group exists
          const groupsResponse = await groupService.getGroups();
          const existingGroup = groupsResponse.data.find(g => g.name === groupName);
          
          if (existingGroup) {
            // Join existing group
            await groupService.addUserToGroup(existingGroup.id, userResponse.data.id);
            console.log('Joined existing group:', existingGroup.name);
          } else {
            // Create new group
            const newGroupResponse = await groupService.createGroup({ name: groupName });
            await groupService.addUserToGroup(newGroupResponse.data.id, userResponse.data.id);
            console.log('Created and joined new group:', groupName);
          }
        } catch (groupErr) {
          console.error('Error with group:', groupErr);
          // Create group if it doesn't exist
          const newGroupResponse = await groupService.createGroup({ name: groupName });
          await groupService.addUserToGroup(newGroupResponse.data.id, userResponse.data.id);
          console.log('Created and joined new group (fallback):', groupName);
        }
      }
      
      console.log('Navigating to dashboard...');
      navigate('/dashboard');
    } catch (err) {
      console.error('Error during new user setup:', err);
      setNewUserError(err.message || 'Failed to create user. Please try again.');
    } finally {
      setNewUserLoading(false);
    }
  };

  // Handle returning user submission
  const handleReturningUserSubmit = async (e) => {
    e.preventDefault();
    setReturningError('');
    setReturningLoading(true);
    
    console.log('Looking up returning user by email:', returningEmail);
    
    try {
      // Validate input
      if (!returningEmail.trim()) {
        throw new Error('Please enter your email');
      }
      
      // Look up user by email
      const response = await userService.lookupByEmail(returningEmail);
      const user = response.data;
      
      console.log('User found:', user);
      
      // Store user info in localStorage
      localStorage.setItem('user_id', user.id);
      localStorage.setItem('username', user.username);
      
      console.log('Navigating to dashboard...');
      navigate('/dashboard');
    } catch (err) {
      console.error('Error looking up user:', err);
      if (err.response && err.response.status === 404) {
        setReturningError('No user found with this email. Please check your email or create a new account.');
      } else {
        setReturningError('An error occurred. Please try again.');
      }
    } finally {
      setReturningLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Account Access
          </Typography>
          
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange} aria-label="account access tabs">
              <Tab label="New User" id="account-tab-0" aria-controls="account-tabpanel-0" />
              <Tab label="Returning User" id="account-tab-1" aria-controls="account-tabpanel-1" />
            </Tabs>
          </Box>
          
          {/* New User Tab */}
          <TabPanel value={tabValue} index={0}>
            <Typography variant="h6" gutterBottom>
              Create Your Account
            </Typography>
            
            {newUserError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {newUserError}
              </Alert>
            )}
            
            <Box component="form" onSubmit={handleNewUserSubmit}>
              <TextField
                label="Your Name"
                fullWidth
                margin="normal"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
              
              <TextField
                label="Email Address"
                type="email"
                fullWidth
                margin="normal"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                helperText="You'll use this to log in next time"
              />
              
              <FormControl component="fieldset" margin="normal">
                <FormLabel component="legend">How would you like to work?</FormLabel>
                <RadioGroup
                  value={workPreference}
                  onChange={(e) => setWorkPreference(e.target.value)}
                >
                  <FormControlLabel value="alone" control={<Radio />} label="I'll work alone" />
                  <FormControlLabel value="group" control={<Radio />} label="I'll work in a group" />
                </RadioGroup>
              </FormControl>
              
              {workPreference === 'group' && (
                <TextField
                  label="Group Name"
                  fullWidth
                  margin="normal"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  required
                  helperText="Enter an existing group or create a new one"
                />
              )}
              
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={newUserLoading}
              >
                {newUserLoading ? 'Creating Account...' : 'Create Account'}
              </Button>
            </Box>
          </TabPanel>
          
          {/* Returning User Tab */}
          <TabPanel value={tabValue} index={1}>
            <Typography variant="h6" gutterBottom>
              Welcome Back
            </Typography>
            
            {returningError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {returningError}
              </Alert>
            )}
            
            <Box component="form" onSubmit={handleReturningUserSubmit}>
              <TextField
                label="Your Email Address"
                type="email"
                fullWidth
                margin="normal"
                value={returningEmail}
                onChange={(e) => setReturningEmail(e.target.value)}
                required
              />
              
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={returningLoading}
              >
                {returningLoading ? 'Looking Up Account...' : 'Continue'}
              </Button>
            </Box>
          </TabPanel>
        </Paper>
      </Box>
    </Container>
  );
};

export default AccountAccessPage;