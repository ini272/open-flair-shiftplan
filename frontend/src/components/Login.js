import React, { useState } from 'react';
import { TextField, Button, Box, Alert } from '@mui/material';
import { authService } from '../services/api';

const Login = ({ onLoginSuccess }) => {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    if (!token.trim()) {
      setError('Please enter a token');
      setLoading(false);
      return;
    }
    
    try {
      console.log('Attempting to login with token...');
      await authService.login(token);
      console.log('Token validated successfully');
      
      // Call the success callback
      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Invalid token. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <TextField
        label="Access Token"
        fullWidth
        margin="normal"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        disabled={loading}
      />
      
      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2 }}
        disabled={loading}
      >
        {loading ? 'Validating...' : 'Login'}
      </Button>
    </Box>
  );
};

export default Login;