import { fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import { clearSubscriptionGate, logout, setCredentials, setSubscriptionGate } from "./authSlice";

let refreshPromise = null;

const buildBaseQuery = (baseUrl) =>
  fetchBaseQuery({
    baseUrl,
    credentials: "include",
    prepareHeaders: (headers, { getState }) => {
      const token = getState().auth.token;
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return headers;
    },
  });

export function createAuthBaseQuery(baseUrl) {
  const authBaseQuery = buildBaseQuery("/api/core/");

  return async (args, api, extraOptions) => {
    const baseUrlOverride = typeof args === "object" && args !== null ? args.baseUrlOverride : undefined;
    const effectiveBaseQuery = buildBaseQuery(baseUrlOverride || baseUrl);
    const sanitizedArgs =
      typeof args === "object" && args !== null
        ? Object.fromEntries(Object.entries(args).filter(([key]) => key !== "baseUrlOverride"))
        : args;

    const requestUrl = typeof sanitizedArgs === "string" ? sanitizedArgs : sanitizedArgs?.url || "";
    let result = await effectiveBaseQuery(sanitizedArgs, api, extraOptions);
    const errorCode = result?.error?.data?.code;
    if (result?.error?.status === 403 && (errorCode === "SUBSCRIPTION_EXPIRED" || errorCode === "COMPANY_SUSPENDED")) {
      api.dispatch(
        setSubscriptionGate({
          code: errorCode,
          message: result?.error?.data?.message || "Subscription access is restricted.",
        })
      );
    } else if (!result?.error && requestUrl && !requestUrl.includes("billing/subscriptions/renew/")) {
      api.dispatch(clearSubscriptionGate());
    }
    const isRefreshEndpoint = requestUrl.includes("auth/refresh/");

    if (result.error?.status !== 401 || isRefreshEndpoint) {
      return result;
    }

    if (!refreshPromise) {
      refreshPromise = (async () => {
        const refreshResult = await authBaseQuery(
          { url: "auth/refresh/", method: "POST" },
          api,
          extraOptions
        );

        if (refreshResult.data?.access) {
          api.dispatch(setCredentials({ access: refreshResult.data.access }));
          return true;
        }

        api.dispatch(logout());
        return false;
      })().finally(() => {
        refreshPromise = null;
      });
    }

    const refreshed = await refreshPromise;
    if (!refreshed) {
      return result;
    }

    result = await effectiveBaseQuery(sanitizedArgs, api, extraOptions);
    return result;
  };
}
