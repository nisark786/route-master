import { createApi } from "@reduxjs/toolkit/query/react";
import { createAuthBaseQuery } from "../auth/createAuthBaseQuery";

const unwrapEnvelope = (payload) => (payload && typeof payload === "object" && "data" in payload ? payload.data : payload);
const normalizeError = (response) => response?.data || response || {};

export const adminApi = createApi({
  reducerPath: "adminApi",
  keepUnusedDataFor: 900,
  refetchOnFocus: false,
  refetchOnReconnect: false,
  baseQuery: createAuthBaseQuery("/api/core/admin/"),
  tagTypes: ["AdminCompanies", "AdminCompanyDetail", "AdminPlans", "AdminPayments", "AdminAnalytics"],
  endpoints: (builder) => ({
    getOverview: builder.query({
      query: () => "overview/",
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: ["AdminAnalytics"],
    }),
    getAnalytics: builder.query({
      query: () => "analytics/",
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: ["AdminAnalytics"],
    }),
    getCompanies: builder.query({
      query: ({ page = 1, page_size = 10, search = "", status = "all" }) =>
        `companies/?page=${page}&page_size=${page_size}&search=${encodeURIComponent(search)}&status=${status}`,
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: ["AdminCompanies"],
    }),
    getCompanyDetail: builder.query({
      query: (companyId) => `companies/${companyId}/`,
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: (_res, _err, companyId) => [{ type: "AdminCompanyDetail", id: companyId }],
    }),
    updateCompanyStatus: builder.mutation({
      query: ({ companyId, body }) => ({
        url: `companies/${companyId}/status/`,
        method: "POST",
        body,
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      invalidatesTags: (_res, _err, { companyId }) => [
        "AdminCompanies",
        { type: "AdminCompanyDetail", id: companyId },
      ],
    }),
    getPlans: builder.query({
      query: () => "plans/",
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: ["AdminPlans"],
    }),
    createPlan: builder.mutation({
      query: (body) => ({
        url: "plans/",
        method: "POST",
        body,
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      invalidatesTags: ["AdminPlans"],
    }),
    updatePlan: builder.mutation({
      query: ({ planId, body }) => ({
        url: `plans/${planId}/`,
        method: "PATCH",
        body,
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      invalidatesTags: ["AdminPlans"],
    }),
    getPlanChangeLogs: builder.query({
      query: () => "plan-change-logs/",
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: ["AdminPlans"],
    }),
    getPayments: builder.query({
      query: ({ page = 1, page_size = 10, search = "", status = "all" }) =>
        `payments/?page=${page}&page_size=${page_size}&search=${encodeURIComponent(search)}&status=${status}`,
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: ["AdminPayments"],
    }),
    getMonitoring: builder.query({
      query: () => "monitoring/",
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: ["AdminAnalytics"],
    }),
  }),
});

export const {
  useGetOverviewQuery,
  useGetAnalyticsQuery,
  useGetCompaniesQuery,
  useGetCompanyDetailQuery,
  useUpdateCompanyStatusMutation,
  useGetPlansQuery,
  useCreatePlanMutation,
  useUpdatePlanMutation,
  useGetPlanChangeLogsQuery,
  useGetPaymentsQuery,
  useGetMonitoringQuery,
} = adminApi;
