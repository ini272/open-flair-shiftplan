import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Box, Paper, Typography, Alert } from '@mui/material';
import Login from '../components/Login';
import Logo from '../components/Logo';
import { translations } from '../utils/translations';

const LoginPage = () => {
  const navigate = useNavigate();

  const onLoginSuccess = () => {
    console.log('Login successful, navigating to account access page...');
    navigate('/access');
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {/* Logo using component */}
        <Box sx={{ mb: 3 }}>
          <Logo size="large" />
        </Box>
        
        <Typography 
          variant="h4" 
          component="h1" 
          gutterBottom 
          sx={{ 
            color: 'primary.main',
            textAlign: 'center',
            fontWeight: 'bold',
            textTransform: 'uppercase',
            letterSpacing: '0.1em'
          }}
        >
          {translations.festival.name}
        </Typography>
        <Typography 
          variant="h6" 
          component="h2" 
          gutterBottom 
          sx={{ 
            color: 'secondary.main',
            textAlign: 'center',
            mb: 4
          }}
        >
          {translations.festival.shiftPlanner}
        </Typography>
        
        <Paper 
          elevation={3} 
          sx={{ 
            p: 4, 
            width: '100%',
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'primary.main'
          }}
        >
          <Login onLoginSuccess={onLoginSuccess} />
        </Paper>
        
        <Typography variant="body2" sx={{ mt: 4, textAlign: 'center', color: 'text.secondary' }}>
          {translations.festival.dates} • {translations.festival.location}
        </Typography>
      </Box>
    </Container>
  );
};

export default LoginPage;