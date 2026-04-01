import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  token: null,
  role: null,
  companyId: null,
  isAuthenticated: false,
  isInitialized: false, 
  subscriptionGate: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action) => {
      const { access, role, company_id } = action.payload;
      const hasProfileData =
        role !== undefined || company_id !== undefined;


      if (access !== undefined) state.token = access;
      
      if (role !== undefined) state.role = role;
      if (company_id !== undefined) state.companyId = company_id;

      state.isAuthenticated = !!(state.token || access);

 
      if (state.isInitialized || hasProfileData) {
        state.isInitialized = true;
      }
    },
    logout: (state) => {
      
      state.token = null;
      state.role = null;
      state.companyId = null;
      state.isAuthenticated = false;
      state.isInitialized = true;
      state.subscriptionGate = null;
    },
    setSubscriptionGate: (state, action) => {
      state.subscriptionGate = action.payload || null;
    },
    clearSubscriptionGate: (state) => {
      state.subscriptionGate = null;
    },
    setInitialized: (state, action) => {
      state.isInitialized = action.payload ?? true;
    },
  },
});

export const { setCredentials, logout, setSubscriptionGate, clearSubscriptionGate, setInitialized } =
  authSlice.actions;
export default authSlice.reducer;
