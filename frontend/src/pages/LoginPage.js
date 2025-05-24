import React from 'react';
import { Container, Box, Paper, Typography } from '@mui/material';
import Login from '../components/Login';

const LoginPage = () => {
  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
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
          Open Flair Festival
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
          Shift Planner 2025
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
          <Login />
        </Paper>
        
        <Typography variant="body2" sx={{ mt: 4, textAlign: 'center', color: 'text.secondary' }}>
          August 6-10, 2025 • Eschwege, Germany
        </Typography>
      </Box>
    </Container>
  );
};

export default LoginPage;