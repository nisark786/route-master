import { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { adminApi } from "./adminApi";

export default function useAdminPrefetch() {
  const dispatch = useDispatch();
  const { isInitialized, isAuthenticated, role } = useSelector((state) => state.auth);
  const hasPrefetchedRef = useRef(false);

  useEffect(() => {
    if (!isInitialized || !isAuthenticated || role !== "SUPER_ADMIN" || hasPrefetchedRef.current) return;
    hasPrefetchedRef.current = true;

    const prefetchOptions = { ifOlderThan: 60 };
    const prefetchQueue = [
      () => dispatch(adminApi.util.prefetch("getOverview", undefined, prefetchOptions)),
      () => dispatch(adminApi.util.prefetch("getAnalytics", undefined, prefetchOptions)),
      () => dispatch(adminApi.util.prefetch("getMonitoring", undefined, prefetchOptions)),
      () =>
        dispatch(
          adminApi.util.prefetch(
            "getCompanies",
            { page: 1, page_size: 10, search: "", status: "all" },
            prefetchOptions
          )
        ),
      () => dispatch(adminApi.util.prefetch("getPlans", undefined, prefetchOptions)),
      () => dispatch(adminApi.util.prefetch("getPlanChangeLogs", undefined, prefetchOptions)),
      () =>
        dispatch(
          adminApi.util.prefetch(
            "getPayments",
            { page: 1, page_size: 10, search: "", status: "all" },
            prefetchOptions
          )
        ),
    ];

    const runQueue = () => {
      prefetchQueue.forEach((runPrefetch, index) => {
        window.setTimeout(runPrefetch, 1500 + index * 400);
      });
    };

    const idleId =
      "requestIdleCallback" in window
        ? window.requestIdleCallback(runQueue, { timeout: 1500 })
        : window.setTimeout(runQueue, 1200);

    return () => {
      if ("cancelIdleCallback" in window) {
        window.cancelIdleCallback(idleId);
      } else {
        window.clearTimeout(idleId);
      }
    };
  }, [dispatch, isInitialized, isAuthenticated, role]);
}
