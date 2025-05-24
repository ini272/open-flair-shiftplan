import React, { useState } from 'react';
import { Box, TextField, Button, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const Login = () => {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!token.trim()) {
      setError('Please enter a token');
      return;
    }
    
    try {
      await api.login(token);
      
      // Check if user ID exists in localStorage
      const userId = localStorage.getItem('user_id');
      if (userId) {
        navigate('/dashboard');
      } else {
        navigate('/setup');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Invalid token. Please try again.');
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <Typography variant="h5" gutterBottom>
        Crew Login
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 2 }}>
        Enter your access token to log in and manage your shifts.
      </Typography>
      
      <TextField
        label="Access Token"
        fullWidth
        margin="normal"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        error={!!error}
        helperText={error}
      />
      
      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2 }}
      >
        Login
      </Button>
    </Box>
  );
};

export default Login;