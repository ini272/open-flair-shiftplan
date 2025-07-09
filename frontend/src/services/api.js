import axios from 'axios';

// Use different API URLs for dev vs prod
const API_URL = process.env.NODE_ENV === 'production' 
  ? `${window.location.protocol}//${window.location.host}` // Use current protocol (https) and host
  : 'http://localhost:8000'; // In development, direct to FastAPI

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Important for cookie-based auth
});

// Auth services
export const authService = {
  login: (token) => api.get(`/auth/login/${token}`),
  logout: () => api.get('/auth/logout'),
  checkAuth: () => api.get('/auth/check'),
};

// User services
export const userService = {
  getUsers: () => api.get('/users'),
  getUser: (id) => api.get(`/users/${id}`),
  createUser: (userData) => api.post('/users', userData),
  updateUser: (id, userData) => api.put(`/users/${id}`, userData),
  deleteUser: (id) => api.delete(`/users/${id}`),
  // Add this new method for email lookup
  lookupByEmail: (email) => api.post('/users/lookup', { email }),
};

// Group services
export const groupService = {
  getGroups: () => api.get('/groups'),
  getGroup: (id) => api.get(`/groups/${id}`),
  createGroup: (groupData) => api.post('/groups', groupData),
  updateGroup: (id, groupData) => api.put(`/groups/${id}`, groupData),
  deleteGroup: (id) => api.delete(`/groups/${id}`),
  addUserToGroup: (groupId, userId) => api.post(`/groups/${groupId}/users/${userId}`),
  removeUserFromGroup: (userId) => api.delete(`/groups/users/${userId}`),
};

// Shift services
export const shiftService = {
  getShifts: (params) => api.get('/shifts', { params }),
  getShift: (id) => api.get(`/shifts/${id}`),
  createShift: (shiftData) => api.post('/shifts', shiftData),
  updateShift: (id, shiftData) => api.put(`/shifts/${id}`, shiftData),
  deleteShift: (id) => api.delete(`/shifts/${id}`),
  addUserToShift: (data) => api.post('/shifts/users/', data),
  addGroupToShift: (data) => api.post('/shifts/groups/', data),
  removeUserFromShift: (shiftId, userId) => api.delete(`/shifts/users/${shiftId}/${userId}`),
  removeGroupFromShift: (shiftId, groupId) => api.delete(`/shifts/groups/${shiftId}/${groupId}`),
  // Add new opt-out endpoints
  optOutUser: (data) => api.post('/shifts/user-opt-out', data),
  optInUser: (data) => api.post('/shifts/user-opt-in', data),
  optOutGroup: (data) => api.post('/shifts/group-opt-out', data),
  optInGroup: (data) => api.post('/shifts/group-opt-in', data),
  checkOptOutStatus: (shiftId, userId) => api.get(`/shifts/opt-out-status/${shiftId}/${userId}`),
  getUserOptOuts: (userId) => api.get(`/shifts/user-opt-outs/${userId}`),
  getGroupOptOuts: (groupId) => api.get(`/shifts/group-opt-outs/${groupId}`),
  getAvailableUsers: (shiftId) => api.get(`/shifts/available-users/${shiftId}`),
  generatePlan: (clearExisting = false, useGroups = true) => api.post('/shifts/generate-plan', null, {
    params: { 
      clear_existing: clearExisting,
      use_groups: useGroups 
    }
  }),
  getCurrentAssignments: () => api.get('/shifts/current-assignments'),
  clearAllAssignments: () => api.delete('/shifts/all-assignments'),
};

// Preference services
export const preferenceService = {
  setPreference: (data) => api.post('/preferences/', data),
  getUserPreferences: (userId) => api.get(`/preferences/users/${userId}`),
  getShiftPreferences: (shiftId, canWork) => api.get(`/preferences/shifts/${shiftId}`, { params: { can_work: canWork } }),
  generateShiftPlan: () => api.post('/shifts/generate-plan'),
};

// Helper function to join a group or create it if it doesn't exist
export const joinGroup = async (data) => {
  try {
    return await api.post('/groups/join', data);
  } catch (error) {
    if (error.response && error.response.status === 404 && data.create_if_not_exists) {
      // Create group and then add user
      const groupResponse = await groupService.createGroup({ name: data.group_name });
      return await groupService.addUserToGroup(groupResponse.data.id, data.user_id);
    }
    throw error;
  }
};

export default {
  login: authService.login,
  logout: authService.logout,
  checkAuth: authService.checkAuth,
  createUser: userService.createUser,
  joinGroup,
};