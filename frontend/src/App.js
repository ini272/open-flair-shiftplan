import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import LoginPage from './pages/LoginPage';
import AccountAccessPage from './pages/AccountAccessPage';
import DashboardPage from './pages/DashboardPage';

// Create an Open Flair themed theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#e30613', // Open Flair red
    },
    secondary: {
      main: '#000000', // Black
    },
    background: {
      default: '#f5f5f5', // Light gray background
      paper: '#ffffff',   // White paper
    },
    text: {
      primary: '#000000', // Black text
      secondary: '#666666', // Gray text
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 700,
    },
    h5: {
      fontWeight: 600,
    },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#000000', // Black app bar
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          textTransform: 'none',
          fontWeight: 600,
        },
        containedPrimary: {
          '&:hover': {
            backgroundColor: '#c00000', // Darker red on hover
          },
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/access" element={<AccountAccessPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/" element={<Navigate to="/login" />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;