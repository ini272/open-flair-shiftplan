import React, { useState, useEffect } from 'react';
import { TextField, Button, Alert, Box, Typography, CircularProgress } from '@mui/material';
import { authService } from '../services/api';
import { translations } from '../utils/translations';

const Login = ({ tokenFromUrl, onLoginSuccess }) => {
  const [token, setToken] = useState(tokenFromUrl || '');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Auto-login effect when component mounts with URL token
  useEffect(() => {
    if (tokenFromUrl) {
      setLoading(true);
      attemptLogin(tokenFromUrl);
    }
  }, [tokenFromUrl]);

  const attemptLogin = async (tokenValue) => {
    try {
      await authService.login(tokenValue);
      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (error) {
      console.error('Login failed:', error);
      setError(translations.auth.invalidToken);
      setToken(tokenValue); // Keep the token in the field for manual retry
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!token.trim()) {
      setError(translations.auth.enterToken);
      return;
    }
    
    setLoading(true);
    await attemptLogin(token);
  };

  // Show loading message during auto-login
  if (loading && tokenFromUrl && !error) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <CircularProgress size={40} sx={{ mb: 2 }} />
        <Typography variant="h6">
          {translations.auth.loggingIn}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" component="h2" gutterBottom align="center">
        {translations.auth.login}
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          label={translations.auth.accessToken}
          placeholder={translations.auth.tokenPlaceholder}
          fullWidth
          margin="normal"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          required
          disabled={loading}
          helperText={translations.auth.tokenHelp}
        />
        
        <Button
          type="submit"
          fullWidth
          variant="contained"
          size="large"
          sx={{ mt: 3, mb: 2 }}
          disabled={loading}
        >
          {loading ? <CircularProgress size={24} color="inherit" /> : translations.auth.login}
        </Button>
      </Box>
    </Box>
  );
};

export default Login;