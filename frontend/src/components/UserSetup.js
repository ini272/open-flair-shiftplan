import React, { useState } from 'react';
import { Box, TextField, Button, Typography, FormControlLabel, Radio, RadioGroup, FormControl, FormLabel } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { userService, groupService } from '../services/api';

const UserSetup = () => {
  const [name, setName] = useState('');
  const [groupName, setGroupName] = useState('');
  const [workPreference, setWorkPreference] = useState('alone');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!name.trim()) {
      setError('Please enter your name');
      return;
    }
    
    if (workPreference === 'group' && !groupName.trim()) {
      setError('Please enter a group name');
      return;
    }
    
    try {
      // Create a user with a generic email
      const email = `${name.toLowerCase().replace(/\s+/g, '.')}@example.com`;
      
      const userResponse = await userService.createUser({
        username: name,
        email: email
      });
      
      // Store user ID in localStorage
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
          } else {
            // Create new group
            const newGroupResponse = await groupService.createGroup({ name: groupName });
            await groupService.addUserToGroup(newGroupResponse.data.id, userResponse.data.id);
          }
        } catch (groupErr) {
          console.error('Error with group:', groupErr);
          // Create group if it doesn't exist
          const newGroupResponse = await groupService.createGroup({ name: groupName });
          await groupService.addUserToGroup(newGroupResponse.data.id, userResponse.data.id);
        }
      }
      
      navigate('/dashboard');
    } catch (err) {
      console.error('Error during setup:', err);
      setError('Failed to create user. Please try again.');
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <Typography variant="h5" gutterBottom>
        Welcome to the Open Flair Shift Planner
      </Typography>
      
      <TextField
        label="Your Name"
        fullWidth
        margin="normal"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      
      <FormControl component="fieldset" sx={{ mb: 2, mt: 2 }}>
        <FormLabel component="legend">How would you like to work?</FormLabel>
        <RadioGroup
          value={workPreference}
          onChange={(e) => setWorkPreference(e.target.value)}
        >
          <FormControlLabel value="alone" control={<Radio />} label="I want to work alone" />
          <FormControlLabel value="group" control={<Radio />} label="I want to work in a group" />
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
          helperText="Enter an existing group name to join it, or a new name to create a group"
        />
      )}
      
      {error && (
        <Typography color="error" sx={{ mt: 2 }}>
          {error}
        </Typography>
      )}
      
      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2 }}
      >
        Continue
      </Button>
    </Box>
  );
};

export default UserSetup;