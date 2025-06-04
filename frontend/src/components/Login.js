import React, { useState } from 'react';
import { TextField, Button, Alert, Box, Typography } from '@mui/material';
import { authService } from '../services/api';
import { translations } from '../utils/translations';

const Login = ({ onLoginSuccess }) => {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!token.trim()) {
      setError(translations.auth.enterToken);
      return;
    }
    
    setLoading(true);
    
    try {
      await authService.login(token);
      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (error) {
      console.error('Login failed:', error);
      setError(translations.auth.invalidToken);
    } finally {
      setLoading(false);
    }
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
          label={translations.auth.accessToken}
          placeholder={translations.auth.tokenPlaceholder}
          fullWidth
          margin="normal"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          required
          disabled={loading}
        />
        
        <Button
          type="submit"
          fullWidth
          variant="contained"
          size="large"
          sx={{ mt: 3, mb: 2 }}
          disabled={loading}
        >
          {loading ? translations.auth.checking : translations.auth.login}
        </Button>
      </Box>
    </Box>
  );
};

export default Login;