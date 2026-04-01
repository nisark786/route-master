import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../features/auth/authSlice';
import { authApi } from '../features/auth/authApi';
import { billingApi } from '../features/billing/billingApi';
import adminReducer from "../features/admin/adminSlice";
import { adminApi } from "../features/admin/adminApi";
import { companyAdminApi } from "../features/companyAdmin/companyAdminApi";
import { chatApi } from "../features/chats/chatApi";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    admin: adminReducer,
    [authApi.reducerPath]: authApi.reducer,
    [billingApi.reducerPath]: billingApi.reducer,
    [adminApi.reducerPath]: adminApi.reducer,
    [companyAdminApi.reducerPath]: companyAdminApi.reducer,
    [chatApi.reducerPath]: chatApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(
      authApi.middleware,
      billingApi.middleware,
      adminApi.middleware,
      companyAdminApi.middleware,
      chatApi.middleware
    ),
});
