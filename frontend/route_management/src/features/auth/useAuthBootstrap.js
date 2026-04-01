import { useEffect, useRef } from "react";
import { useDispatch } from "react-redux";
import { useLazyMeQuery, useRefreshMutation } from "./authApi";
import { logout, setCredentials, setInitialized } from "./authSlice";

let bootstrapStarted = false;

export default function useAuthBootstrap() {
  const dispatch = useDispatch();
  const [refresh] = useRefreshMutation();
  const [triggerMe] = useLazyMeQuery();
  const hasInitializedRef = useRef(false);

  useEffect(() => {
    if (hasInitializedRef.current || bootstrapStarted) return;
    hasInitializedRef.current = true;
    bootstrapStarted = true;

    const initializeSession = async () => {
      try {
        const refreshData = await refresh().unwrap();
        dispatch(setCredentials({ access: refreshData.access }));
        dispatch(setInitialized(true));

        try {
          const meData = await triggerMe().unwrap();
          dispatch(setCredentials(meData));
        } catch {
          dispatch(logout());
        }
      } catch {
        dispatch(logout());
      } finally {
        bootstrapStarted = false;
      }
    };

    initializeSession();
  }, [dispatch, refresh, triggerMe]);
}
