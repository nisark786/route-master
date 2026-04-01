import { createApi } from "@reduxjs/toolkit/query/react";
import { createAuthBaseQuery } from "../auth/createAuthBaseQuery";

const normalizeError = (response) => response?.data || response || {};
const unwrapEnvelope = (payload) => (payload && typeof payload === "object" && "data" in payload ? payload.data : payload);

export const companyAdminApi = createApi({
  reducerPath: "companyAdminApi",
  baseQuery: createAuthBaseQuery("/api/core/company-admin/"),
  tagTypes: [
    "CompanyVehicles",
    "CompanyProducts",
    "CompanyShops",
    "CompanyRoutes",
    "CompanyRouteAvailableShops",
    "CompanyDrivers",
    "CompanyDriverAssignments",
    "CompanyLiveTracking",
    "CompanyRbacPermissions",
    "CompanyRbacRoles",
    "CompanyRbacAssignments",
    "CompanyDashboard",
    "CompanyOperations",
  ],
  endpoints: (builder) => ({
    getDashboardOverview: builder.query({
      query: () => "dashboard/overview/",
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: [{ type: "CompanyDashboard", id: "OVERVIEW" }],
    }),
    getVehicles: builder.query({
      query: () => "vehicles/",
      transformErrorResponse: normalizeError,
      providesTags: ["CompanyVehicles"],
    }),
    createVehicle: builder.mutation({
      query: (body) => ({
        url: "vehicles/",
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: ["CompanyVehicles"],
    }),
    createMediaUploadUrl: builder.mutation({
      query: (body) => ({
        url: "media/presign/",
        method: "POST",
        body,
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
    }),
    updateVehicle: builder.mutation({
      query: ({ vehicleId, body }) => ({
        url: `vehicles/${vehicleId}/`,
        method: "PATCH",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: ["CompanyVehicles"],
    }),
    deleteVehicle: builder.mutation({
      query: (vehicleId) => ({
        url: `vehicles/${vehicleId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: ["CompanyVehicles"],
    }),
    getProducts: builder.query({
      query: () => "products/",
      transformErrorResponse: normalizeError,
      providesTags: (result) =>
        result
          ? [
              ...result.map((product) => ({ type: "CompanyProducts", id: product.id })),
              { type: "CompanyProducts", id: "LIST" },
            ]
          : [{ type: "CompanyProducts", id: "LIST" }],
    }),
    createProduct: builder.mutation({
      query: (body) => {
        const formData = new FormData();
        Object.entries(body || {}).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            formData.append(key, value);
          }
        });
        return {
          url: "products/",
          method: "POST",
          body: formData,
        };
      },
      transformErrorResponse: normalizeError,
      invalidatesTags: [{ type: "CompanyProducts", id: "LIST" }],
    }),
    updateProduct: builder.mutation({
      query: ({ productId, body }) => {
        const formData = new FormData();
        Object.entries(body || {}).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            formData.append(key, value);
          }
        });
        return {
          url: `products/${productId}/`,
          method: "PATCH",
          body: formData,
        };
      },
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyProducts", id: arg.productId },
        { type: "CompanyProducts", id: "LIST" },
      ],
    }),
    deleteProduct: builder.mutation({
      query: (productId) => ({
        url: `products/${productId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, productId) => [
        { type: "CompanyProducts", id: productId },
        { type: "CompanyProducts", id: "LIST" },
      ],
    }),
    getShops: builder.query({
      query: ({ search = "", page = 1 } = {}) => ({
        url: "shops/",
        params: { search, page },
      }),
      transformErrorResponse: normalizeError,
      providesTags: (result) =>
        result?.results
          ? [
              ...result.results.map((shop) => ({ type: "CompanyShops", id: shop.id })),
              { type: "CompanyShops", id: "LIST" },
            ]
          : [{ type: "CompanyShops", id: "LIST" }],
    }),
    createShop: builder.mutation({
      query: (body) => {
        const formData = new FormData();
        Object.entries(body || {}).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            formData.append(key, value);
          }
        });
        return {
          url: "shops/",
          method: "POST",
          body: formData,
        };
      },
      transformErrorResponse: normalizeError,
      invalidatesTags: [{ type: "CompanyShops", id: "LIST" }],
    }),
    updateShop: builder.mutation({
      query: ({ shopId, body }) => {
        const formData = new FormData();
        Object.entries(body || {}).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            formData.append(key, value);
          }
        });
        return {
          url: `shops/${shopId}/`,
          method: "PATCH",
          body: formData,
        };
      },
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyShops", id: arg.shopId },
        { type: "CompanyShops", id: "LIST" },
      ],
    }),
    deleteShop: builder.mutation({
      query: (shopId) => ({
        url: `shops/${shopId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, shopId) => [
        { type: "CompanyShops", id: shopId },
        { type: "CompanyShops", id: "LIST" },
      ],
    }),
    resetShopOwnerPassword: builder.mutation({
      query: ({ shopId, body }) => ({
        url: `shops/${shopId}/owner/reset-password/`,
        method: "POST",
        body: body || {},
      }),
      transformErrorResponse: normalizeError,
    }),
    getRoutes: builder.query({
      query: ({ search = "" } = {}) => ({
        url: "routes/",
        params: { search },
      }),
      transformErrorResponse: normalizeError,
      providesTags: (result) =>
        result
          ? [
              ...result.map((route) => ({ type: "CompanyRoutes", id: route.id })),
              { type: "CompanyRoutes", id: "LIST" },
            ]
          : [{ type: "CompanyRoutes", id: "LIST" }],
    }),
    getRouteDetail: builder.query({
      query: (routeId) => `routes/${routeId}/`,
      transformErrorResponse: normalizeError,
      providesTags: (result, error, routeId) => [{ type: "CompanyRoutes", id: routeId }],
    }),
    getAvailableRouteShops: builder.query({
      query: () => "routes/available-shops/",
      transformErrorResponse: normalizeError,
      providesTags: [{ type: "CompanyRouteAvailableShops", id: "LIST" }],
    }),
    createRoute: builder.mutation({
      query: (body) => ({
        url: "routes/",
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [
        { type: "CompanyRoutes", id: "LIST" },
        { type: "CompanyRouteAvailableShops", id: "LIST" },
      ],
    }),
    updateRoute: builder.mutation({
      query: ({ routeId, body }) => ({
        url: `routes/${routeId}/`,
        method: "PATCH",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyRoutes", id: arg.routeId },
        { type: "CompanyRoutes", id: "LIST" },
        { type: "CompanyRouteAvailableShops", id: "LIST" },
      ],
    }),
    deleteRoute: builder.mutation({
      query: (routeId) => ({
        url: `routes/${routeId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [
        { type: "CompanyRoutes", id: "LIST" },
        { type: "CompanyRouteAvailableShops", id: "LIST" },
      ],
    }),
    addShopToRoute: builder.mutation({
      query: ({ routeId, body }) => ({
        url: `routes/${routeId}/shops/`,
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyRoutes", id: arg.routeId },
        { type: "CompanyRoutes", id: "LIST" },
        { type: "CompanyRouteAvailableShops", id: "LIST" },
      ],
    }),
    removeShopFromRoute: builder.mutation({
      query: ({ routeId, shopId }) => ({
        url: `routes/${routeId}/shops/${shopId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyRoutes", id: arg.routeId },
        { type: "CompanyRoutes", id: "LIST" },
        { type: "CompanyRouteAvailableShops", id: "LIST" },
      ],
    }),
    updateRouteShopPosition: builder.mutation({
      query: ({ routeId, shopId, position }) => ({
        url: `routes/${routeId}/shops/${shopId}/position/`,
        method: "PATCH",
        body: { position },
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyRoutes", id: arg.routeId },
        { type: "CompanyRoutes", id: "LIST" },
      ],
    }),
    getDrivers: builder.query({
      query: ({ search = "" } = {}) => ({
        url: "drivers/",
        params: { search },
      }),
      transformErrorResponse: normalizeError,
      providesTags: (result) =>
        result
          ? [
              ...result.map((driver) => ({ type: "CompanyDrivers", id: driver.id })),
              { type: "CompanyDrivers", id: "LIST" },
            ]
          : [{ type: "CompanyDrivers", id: "LIST" }],
    }),
    getDriverDetail: builder.query({
      query: (driverId) => `drivers/${driverId}/`,
      transformErrorResponse: normalizeError,
      providesTags: (result, error, driverId) => [{ type: "CompanyDrivers", id: driverId }],
    }),
    createDriver: builder.mutation({
      query: (body) => ({
        url: "drivers/",
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [{ type: "CompanyDrivers", id: "LIST" }],
    }),
    updateDriver: builder.mutation({
      query: ({ driverId, body }) => ({
        url: `drivers/${driverId}/`,
        method: "PATCH",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyDrivers", id: arg.driverId },
        { type: "CompanyDrivers", id: "LIST" },
      ],
    }),
    deleteDriver: builder.mutation({
      query: (driverId) => ({
        url: `drivers/${driverId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [
        { type: "CompanyDrivers", id: "LIST" },
        { type: "CompanyDriverAssignments", id: "LIST" },
      ],
    }),
    resetDriverPassword: builder.mutation({
      query: ({ driverId, body }) => ({
        url: `drivers/${driverId}/reset-password/`,
        method: "POST",
        body: body || {},
      }),
      transformErrorResponse: normalizeError,
    }),
    getDriverAssignments: builder.query({
      query: (driverId) => `drivers/${driverId}/assignments/`,
      transformErrorResponse: normalizeError,
      providesTags: (result, error, driverId) =>
        result
          ? [
              ...result.map((item) => ({ type: "CompanyDriverAssignments", id: item.id })),
              { type: "CompanyDriverAssignments", id: `LIST-${driverId}` },
            ]
          : [{ type: "CompanyDriverAssignments", id: `LIST-${driverId}` }],
    }),
    getCompanyAssignments: builder.query({
      query: ({ search = "", status = "all" } = {}) => ({
        url: "drivers/assignments/",
        params: { search, status },
      }),
      transformErrorResponse: normalizeError,
      providesTags: (result) =>
        result
          ? [
              ...result.map((item) => ({ type: "CompanyDriverAssignments", id: item.id })),
              { type: "CompanyDriverAssignments", id: "COMPANY-LIST" },
            ]
          : [{ type: "CompanyDriverAssignments", id: "COMPANY-LIST" }],
    }),
    getOperationsExecutions: builder.query({
      query: ({ date, search = "", status = "all" } = {}) => ({
        url: "operations/executions/",
        params: { date, search, status },
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: [{ type: "CompanyOperations", id: "LIST" }],
    }),
    getOperationExecutionDetail: builder.query({
      query: (assignmentId) => `operations/executions/${assignmentId}/`,
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: (result, error, assignmentId) => [{ type: "CompanyOperations", id: assignmentId }],
    }),
    getLiveTrackingVehicles: builder.query({
      query: () => "live-tracking/vehicles/",
      transformErrorResponse: normalizeError,
      providesTags: [{ type: "CompanyLiveTracking", id: "VEHICLES" }],
    }),
    getLiveTrackingVehicleDetail: builder.query({
      query: (vehicleId) => `live-tracking/vehicles/${vehicleId}/`,
      transformErrorResponse: normalizeError,
      providesTags: (result, error, vehicleId) => [{ type: "CompanyLiveTracking", id: vehicleId }],
    }),
    createDriverAssignment: builder.mutation({
      query: ({ driverId, body }) => ({
        url: `drivers/${driverId}/assignments/`,
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyDriverAssignments", id: `LIST-${arg.driverId}` },
        { type: "CompanyDriverAssignments", id: "COMPANY-LIST" },
        { type: "CompanyDrivers", id: arg.driverId },
        { type: "CompanyOperations", id: "LIST" },
        { type: "CompanyDashboard", id: "OVERVIEW" },
      ],
    }),
    updateDriverAssignment: builder.mutation({
      query: ({ driverId, assignmentId, body }) => ({
        url: `drivers/${driverId}/assignments/${assignmentId}/`,
        method: "PATCH",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyDriverAssignments", id: arg.assignmentId },
        { type: "CompanyDriverAssignments", id: `LIST-${arg.driverId}` },
        { type: "CompanyDriverAssignments", id: "COMPANY-LIST" },
      ],
    }),
    deleteDriverAssignment: builder.mutation({
      query: ({ driverId, assignmentId }) => ({
        url: `drivers/${driverId}/assignments/${assignmentId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: (result, error, arg) => [
        { type: "CompanyDriverAssignments", id: arg.assignmentId },
        { type: "CompanyDriverAssignments", id: `LIST-${arg.driverId}` },
        { type: "CompanyDriverAssignments", id: "COMPANY-LIST" },
      ],
    }),
    getRbacPermissions: builder.query({
      query: () => "rbac/permissions/",
      transformErrorResponse: normalizeError,
      providesTags: [{ type: "CompanyRbacPermissions", id: "LIST" }],
    }),
    getRbacRoles: builder.query({
      query: () => "rbac/roles/",
      transformErrorResponse: normalizeError,
      providesTags: [{ type: "CompanyRbacRoles", id: "LIST" }],
    }),
    createRbacRole: builder.mutation({
      query: (body) => ({
        url: "rbac/roles/",
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [{ type: "CompanyRbacRoles", id: "LIST" }],
    }),
    updateRbacRole: builder.mutation({
      query: ({ roleId, body }) => ({
        url: `rbac/roles/${roleId}/`,
        method: "PATCH",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [{ type: "CompanyRbacRoles", id: "LIST" }],
    }),
    deleteRbacRole: builder.mutation({
      query: (roleId) => ({
        url: `rbac/roles/${roleId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [{ type: "CompanyRbacRoles", id: "LIST" }],
    }),
    getRbacAssignments: builder.query({
      query: () => "rbac/user-roles/",
      transformErrorResponse: normalizeError,
      providesTags: [{ type: "CompanyRbacAssignments", id: "LIST" }],
    }),
    assignRbacRoleToUser: builder.mutation({
      query: (body) => ({
        url: "rbac/user-roles/",
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [{ type: "CompanyRbacAssignments", id: "LIST" }],
    }),
    deleteRbacAssignment: builder.mutation({
      query: (assignmentId) => ({
        url: `rbac/user-roles/${assignmentId}/`,
        method: "DELETE",
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [{ type: "CompanyRbacAssignments", id: "LIST" }],
    }),
    askAiAssistant: builder.mutation({
      query: (body) => ({
        baseUrlOverride: "/",
        url: "/api/ai/chat",
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
    }),
    getAiDispatchCopilot: builder.mutation({
      query: (body = {}) => ({
        baseUrlOverride: "/",
        url: "/api/ai/dispatch-copilot",
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
    }),
    approveAiDispatchCopilot: builder.mutation({
      query: (body) => ({
        baseUrlOverride: "/",
        url: "/api/ai/dispatch-copilot/approve",
        method: "POST",
        body,
      }),
      transformErrorResponse: normalizeError,
      invalidatesTags: [
        { type: "CompanyDriverAssignments", id: "COMPANY-LIST" },
        { type: "CompanyOperations", id: "LIST" },
        { type: "CompanyDashboard", id: "OVERVIEW" },
      ],
    }),
    triggerAiSync: builder.mutation({
      query: () => ({
        url: "ai/sync/",
        method: "POST",
      }),
      transformErrorResponse: normalizeError,
    }),
  }),
});

export const {
  useGetDashboardOverviewQuery,
  useGetVehiclesQuery,
  useCreateVehicleMutation,
  useCreateMediaUploadUrlMutation,
  useUpdateVehicleMutation,
  useDeleteVehicleMutation,
  useGetProductsQuery,
  useCreateProductMutation,
  useUpdateProductMutation,
  useDeleteProductMutation,
  useGetShopsQuery,
  useCreateShopMutation,
  useUpdateShopMutation,
  useDeleteShopMutation,
  useResetShopOwnerPasswordMutation,
  useGetRoutesQuery,
  useGetRouteDetailQuery,
  useLazyGetRouteDetailQuery,
  useGetAvailableRouteShopsQuery,
  useCreateRouteMutation,
  useUpdateRouteMutation,
  useDeleteRouteMutation,
  useAddShopToRouteMutation,
  useRemoveShopFromRouteMutation,
  useUpdateRouteShopPositionMutation,
  useGetDriversQuery,
  useGetDriverDetailQuery,
  useCreateDriverMutation,
  useUpdateDriverMutation,
  useDeleteDriverMutation,
  useResetDriverPasswordMutation,
  useGetDriverAssignmentsQuery,
  useGetCompanyAssignmentsQuery,
  useGetOperationsExecutionsQuery,
  useLazyGetOperationExecutionDetailQuery,
  useGetLiveTrackingVehiclesQuery,
  useGetLiveTrackingVehicleDetailQuery,
  useCreateDriverAssignmentMutation,
  useUpdateDriverAssignmentMutation,
  useDeleteDriverAssignmentMutation,
  useGetRbacPermissionsQuery,
  useGetRbacRolesQuery,
  useCreateRbacRoleMutation,
  useUpdateRbacRoleMutation,
  useDeleteRbacRoleMutation,
  useGetRbacAssignmentsQuery,
  useAssignRbacRoleToUserMutation,
  useDeleteRbacAssignmentMutation,
  useAskAiAssistantMutation,
  useGetAiDispatchCopilotMutation,
  useApproveAiDispatchCopilotMutation,
  useTriggerAiSyncMutation,
} = companyAdminApi;
