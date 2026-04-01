import { createApi } from "@reduxjs/toolkit/query/react";
import { createAuthBaseQuery } from "../auth/createAuthBaseQuery";

export const billingApi = createApi({
  reducerPath: "billingApi",
  baseQuery: createAuthBaseQuery("/api/core/"),
  endpoints: (builder) => ({
    getPlans: builder.query({
      query: () => "billing/plans/",
    }),
    startRegistration: builder.mutation({
      query: (body) => ({
        url: "billing/registrations/start/",
        method: "POST",
        body,
      }),
    }),
    verifyOtp: builder.mutation({
      query: (body) => ({
        url: "billing/registrations/verify-otp/",
        method: "POST",
        body,
      }),
    }),
    resendOtp: builder.mutation({
      query: (body) => ({
        url: "billing/registrations/resend-otp/",
        method: "POST",
        body,
      }),
    }),
    createOrder: builder.mutation({
      query: (body) => ({
        url: "billing/registrations/create-order/",
        method: "POST",
        body,
      }),
    }),
    completeRegistration: builder.mutation({
      query: (body) => ({
        url: "billing/registrations/complete/",
        method: "POST",
        body,
      }),
    }),
    createRenewalOrder: builder.mutation({
      query: (body) => ({
        url: "billing/subscriptions/renew/create-order/",
        method: "POST",
        body,
      }),
    }),
    completeRenewal: builder.mutation({
      query: (body) => ({
        url: "billing/subscriptions/renew/complete/",
        method: "POST",
        body,
      }),
    }),
    getCompanyProfile: builder.query({
      query: () => "company/profile/",
    }),
    updateCompanyProfile: builder.mutation({
      query: (body) => ({
        url: "company/profile/",
        method: "PATCH",
        body,
      }),
    }),
    getBillingTransactions: builder.query({
      query: () => "billing/subscriptions/transactions/",
    }),
    changePassword: builder.mutation({
      query: (body) => ({
        url: "auth/change-initial-password/",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const {
  useGetPlansQuery,
  useStartRegistrationMutation,
  useVerifyOtpMutation,
  useResendOtpMutation,
  useCreateOrderMutation,
  useCompleteRegistrationMutation,
  useCreateRenewalOrderMutation,
  useCompleteRenewalMutation,
  useGetCompanyProfileQuery,
  useUpdateCompanyProfileMutation,
  useGetBillingTransactionsQuery,
  useChangePasswordMutation,
} = billingApi;
