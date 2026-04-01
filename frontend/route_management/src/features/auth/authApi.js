import { createApi } from "@reduxjs/toolkit/query/react";

import { createAuthBaseQuery } from "./createAuthBaseQuery";

export const authApi = createApi({
  reducerPath: "authApi",
  baseQuery: createAuthBaseQuery("/api/core/"),
  tagTypes: ["User"],
  endpoints: (builder) => ({
    login: builder.mutation({
      query: (credentials) => ({
        url: "auth/web/login/",
        method: "POST",
        body: credentials,
      }),
    }),
    refresh: builder.mutation({
      query: () => ({
        url: "auth/refresh/",
        method: "POST",
      }),
    }),
    me: builder.query({
      query: () => "auth/me/",
      providesTags: ["User"],
    }),
    logout: builder.mutation({
      query: () => ({
        url: "auth/logout/",
        method: "POST",
      }),
    }),
  }),
});

export const { useLoginMutation, useRefreshMutation, useLazyMeQuery, useLogoutMutation } = authApi;
