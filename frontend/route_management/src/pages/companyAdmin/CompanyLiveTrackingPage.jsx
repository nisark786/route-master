import { useEffect, useMemo, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip } from "react-leaflet";
import L from "leaflet";
import { toast } from "react-toastify";
import { useMap } from "react-leaflet";

import {
  useGetLiveTrackingVehicleDetailQuery,
  useGetLiveTrackingVehiclesQuery,
} from "../../features/companyAdmin/companyAdminApi";
import { useRefreshMutation } from "../../features/auth/authApi";
import { setCredentials } from "../../features/auth/authSlice";
import { extractApiErrorMessage } from "../../utils/adminUi";
import { getRuntimeConfig } from "../../config/runtimeConfig";

const markerIcon = L.icon({
  iconRetinaUrl: new URL("leaflet/dist/images/marker-icon-2x.png", import.meta.url).toString(),
  iconUrl: new URL("leaflet/dist/images/marker-icon.png", import.meta.url).toString(),
  shadowUrl: new URL("leaflet/dist/images/marker-shadow.png", import.meta.url).toString(),
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

function toLatLng(point) {
  const lat = Number(point?.latitude);
  const lng = Number(point?.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return null;
  }
  return [lat, lng];
}

function AutoFollow({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) {
      map.setView(position, map.getZoom(), { animate: true });
    }
  }, [position, map]);
  return null;
}

function parseJwt(token) {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

export default function CompanyLiveTrackingPage() {
  const dispatch = useDispatch();
  const token = useSelector((state) => state.auth.token);
  const [refresh] = useRefreshMutation();
  const refreshInFlight = useRef(false);
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const [liveDetail, setLiveDetail] = useState(null);
  const { data: vehicles = [], error: listError } = useGetLiveTrackingVehiclesQuery();
  const effectiveSelectedVehicleId = selectedVehicleId || vehicles[0]?.vehicle_id || "";
  const { data: detailData, error: detailError } = useGetLiveTrackingVehicleDetailQuery(effectiveSelectedVehicleId, {
    skip: !effectiveSelectedVehicleId,
  });

  const feedback = useMemo(() => extractApiErrorMessage(listError) || extractApiErrorMessage(detailError), [listError, detailError]);
  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `company-live-tracking-${feedback}` });
    }
  }, [feedback]);

  const currentLiveDetail = liveDetail || detailData;
  const liveDetailRef = useRef(currentLiveDetail);
  useEffect(() => {
    liveDetailRef.current = currentLiveDetail;
  }, [currentLiveDetail]);

  useEffect(() => {
    if (!currentLiveDetail?.assignment_id || !token || !currentLiveDetail?.company_id) {
      return undefined;
    }

    const tokenPayload = parseJwt(token);
    const expSeconds = Number(tokenPayload?.exp || 0);
    const nowSeconds = Math.floor(Date.now() / 1000);
    if (expSeconds && expSeconds <= nowSeconds + 30) {
      if (!refreshInFlight.current) {
        refreshInFlight.current = true;
        refresh()
          .unwrap()
          .then((data) => {
            if (data?.access) {
              dispatch(setCredentials({ access: data.access }));
            }
          })
          .finally(() => {
            refreshInFlight.current = false;
          });
      }
      return undefined;
    }

    const companyId = currentLiveDetail.company_id;
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsBase = getRuntimeConfig(
      "VITE_WS_BASE_URL",
      import.meta.env.VITE_WS_BASE_URL || `${wsProtocol}//${window.location.host}`
    );
    const ws = new WebSocket(`${wsBase}/ws/live-tracking/company/${companyId}/?token=${encodeURIComponent(token)}`);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.assignment_id !== liveDetailRef.current?.assignment_id) {
          return;
        }
        if (payload.event === "location_update") {
          setLiveDetail((prev) => {
            const base = prev || liveDetailRef.current;
            if (!base) return base;
            const nextHistory = [...(base.route_history || []), payload].slice(-4000);
            return {
              ...base,
              latest_location: payload,
              route_history: nextHistory,
            };
          });
        } else if (payload.event === "stop_update") {
          setLiveDetail((prev) => {
            const base = prev || liveDetailRef.current;
            if (!base) return base;
            const updatedShops = (base.shops || []).map((shop) => {
              if (shop.shop_id !== payload.shop_id) return shop;
              return {
                ...shop,
                status: payload.status,
                check_in_at: payload.check_in_at || shop.check_in_at,
                check_out_at: payload.check_out_at || shop.check_out_at,
                skipped_at: payload.skipped_at || shop.skipped_at,
                skip_reason: payload.skip_reason || shop.skip_reason,
              };
            });
            const completedOrSkipped = updatedShops.filter(
              (item) => item.status === "COMPLETED" || item.status === "SKIPPED"
            );
            return {
              ...base,
              shops: updatedShops,
              completed_or_skipped_shops: completedOrSkipped,
            };
          });
        }
      } catch {
        // ignore malformed websocket payload
      }
    };
    ws.onclose = (event) => {
      if (event?.code === 4401 && !refreshInFlight.current) {
        refreshInFlight.current = true;
        refresh()
          .unwrap()
          .then((data) => {
            if (data?.access) {
              dispatch(setCredentials({ access: data.access }));
            }
          })
          .finally(() => {
            refreshInFlight.current = false;
          });
      }
    };
    return () => {
      ws.close();
    };
  }, [currentLiveDetail?.assignment_id, currentLiveDetail?.company_id, token, refresh, dispatch]);

  const gonePath = useMemo(
    () => (currentLiveDetail?.route_history || []).map((item) => toLatLng(item)).filter(Boolean),
    [currentLiveDetail?.route_history]
  );
  const remainingPath = useMemo(() => {
    const pendingStops = (currentLiveDetail?.shops || [])
      .filter((item) => item.status === "PENDING" || item.status === "CHECKED_IN")
      .sort((a, b) => Number(a.position || 0) - Number(b.position || 0))
      .map((item) => toLatLng(item))
      .filter(Boolean);

    const start = toLatLng(currentLiveDetail?.latest_location);
    if (start && pendingStops.length) {
      return [start, ...pendingStops];
    }
    return pendingStops;
  }, [currentLiveDetail?.shops, currentLiveDetail?.latest_location]);
  const shopPoints = useMemo(
    () => (currentLiveDetail?.shops || []).map((item) => ({ ...item, latLng: toLatLng(item) })).filter((item) => item.latLng),
    [currentLiveDetail?.shops]
  );
  const latest = toLatLng(currentLiveDetail?.latest_location);

  const mapCenter = latest || shopPoints[0]?.latLng || [10.8505, 76.2711];

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Live Tracking</h1>
          <p className="text-slate-500 font-medium text-sm">Track in-route vehicles and stop outcomes in real time.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
        <aside className="bg-white border border-slate-200 rounded-2xl p-3 space-y-2 h-155 overflow-y-auto">
          <p className="text-xs font-black uppercase tracking-wider text-slate-400 px-1">Active Vehicles</p>
          {!vehicles.length ? <p className="text-sm text-slate-500 font-semibold p-2">No in-route vehicles.</p> : null}
          {vehicles.map((item) => (
            <button
              key={item.vehicle_id}
              type="button"
              className={`w-full text-left rounded-xl border px-3 py-3 transition ${
                effectiveSelectedVehicleId === item.vehicle_id ? "border-blue-500 bg-blue-50" : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
              onClick={() => {
                setSelectedVehicleId(item.vehicle_id);
                setLiveDetail(null);
              }}
            >
              <p className="text-sm font-black text-slate-800">{item.vehicle_name}</p>
              <p className="text-xs font-semibold text-slate-500">{item.vehicle_number_plate}</p>
              <p className="text-xs font-semibold text-slate-600 mt-1">Driver: {item.driver_name}</p>
              <p className="text-xs font-semibold text-slate-500">Route: {item.route_name}</p>
            </button>
          ))}
        </aside>

        <section className="space-y-3">
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
            <MapContainer center={mapCenter} zoom={13} scrollWheelZoom className="h-120 w-full">
              <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              {latest ? <AutoFollow position={latest} /> : null}

              {gonePath.length >= 2 ? <Polyline positions={gonePath} pathOptions={{ color: "#2563eb", weight: 5 }} /> : null}
              {remainingPath.length >= 2 ? (
                <Polyline
                  positions={remainingPath}
                  pathOptions={{ color: "#16a34a", weight: 4, dashArray: "8, 10" }}
                />
              ) : null}

              {shopPoints.map((shop) => {
                const color =
                  shop.status === "COMPLETED" ? "#16a34a" : shop.status === "SKIPPED" ? "#dc2626" : shop.status === "CHECKED_IN" ? "#ea580c" : "#64748b";
                const shopIcon = L.divIcon({
                  className: "custom-shop-icon",
                  html: `<div style="background:${color};width:14px;height:14px;border-radius:50%;border:2px solid white;"></div>`,
                  iconSize: [14, 14],
                  iconAnchor: [7, 7],
                });
                return (
                  <Marker key={shop.shop_id} position={shop.latLng} icon={shopIcon}>
                    <Tooltip direction="top" offset={[0, -8]} opacity={1}>
                      <div className="text-xs font-bold">
                        {shop.name} ({shop.status})
                      </div>
                    </Tooltip>
                  </Marker>
                );
              })}

              {latest ? (
                <Marker position={latest} icon={markerIcon}>
                  <Tooltip direction="top" offset={[0, -8]} opacity={1}>
                    <div className="text-xs font-bold">Vehicle Live Location</div>
                  </Tooltip>
                </Marker>
              ) : null}
            </MapContainer>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-4">
            <p className="text-xs font-black uppercase tracking-wider text-slate-400">Completed / Skipped Stops</p>
            <div className="mt-3 space-y-2 max-h-44 overflow-y-auto">
              {(currentLiveDetail?.completed_or_skipped_shops || []).length ? (
                currentLiveDetail.completed_or_skipped_shops.map((item) => (
                  <div key={item.shop_id} className="border border-slate-200 rounded-xl p-3 bg-slate-50">
                    <p className="text-sm font-black text-slate-800">{item.name}</p>
                    <p className="text-xs font-semibold text-slate-500">
                      Status: {item.status} | Position: {item.position}
                    </p>
                    <p className="text-xs text-slate-500 font-medium">{item.location_display_name || "-"}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm font-semibold text-slate-500">No completed/skipped stops yet.</p>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
