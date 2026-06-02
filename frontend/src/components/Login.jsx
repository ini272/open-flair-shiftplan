import React, { useState } from 'react';
import { TextField, Button, Alert, Box, Typography, CircularProgress } from '@mui/material';
import { authService } from '../services/api';
import { translations } from '../utils/translations';

const Login = ({ onLoginSuccess }) => {
  const [accessCode, setAccessCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const attemptLogin = async (accessCodeValue) => {
    try {
      await authService.login(accessCodeValue);
      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (error) {
      console.error('Login failed:', error);
      setError(translations.auth.invalidAccessCode);
      setAccessCode(accessCodeValue);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!accessCode.trim()) {
      setError(translations.auth.enterAccessCode);
      return;
    }
    
    setLoading(true);
    await attemptLogin(accessCode);
  };

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
          label={translations.auth.accessCode}
          placeholder={translations.auth.accessCodePlaceholder}
          fullWidth
          margin="normal"
          value={accessCode}
          onChange={(e) => setAccessCode(e.target.value)}
          required
          disabled={loading}
          helperText={translations.auth.accessCodeHelp}
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
