import { useMemo, useState } from "react";
import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";
import L from "leaflet";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL("leaflet/dist/images/marker-icon-2x.png", import.meta.url).toString(),
  iconUrl: new URL("leaflet/dist/images/marker-icon.png", import.meta.url).toString(),
  shadowUrl: new URL("leaflet/dist/images/marker-shadow.png", import.meta.url).toString(),
});

const DEFAULT_CENTER = { lat: 10.8505, lng: 76.2711 };
const DEFAULT_ZOOM = 11;

function ClickableMarker({ value, onChange }) {
  useMapEvents({
    click(e) {
      onChange({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });

  if (!value) return null;
  return <Marker position={[value.lat, value.lng]} />;
}

async function reverseGeocode(lat, lng) {
  const endpoint = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}`;
  const response = await fetch(endpoint, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) return "";
  const payload = await response.json();
  return payload?.display_name || "";
}

export default function MapLocationPickerModal({
  isOpen,
  initialValue,
  initialDisplayName = "",
  onClose,
  onConfirm,
}) {
  const [selected, setSelected] = useState(initialValue || null);
  const [displayName, setDisplayName] = useState(initialDisplayName || "");
  const [isResolving, setIsResolving] = useState(false);

  const center = useMemo(() => {
    if (selected) return selected;
    if (initialValue) return initialValue;
    return DEFAULT_CENTER;
  }, [selected, initialValue]);

  if (!isOpen) return null;

  const onMapPick = async (coords) => {
    setSelected(coords);
    setIsResolving(true);
    try {
      const resolved = await reverseGeocode(coords.lat, coords.lng);
      if (resolved) setDisplayName(resolved);
    } catch {
      // keep manual entry fallback when reverse geocoding fails
    } finally {
      setIsResolving(false);
    }
  };

  const submit = () => {
    if (!selected) return;
    onConfirm({
      latitude: Number(selected.lat).toFixed(6),
      longitude: Number(selected.lng).toFixed(6),
      location_display_name: displayName.trim(),
      location: displayName.trim(),
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-base font-black text-slate-900">Pick Shop Location</h3>
          <button
            type="button"
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-black uppercase tracking-widest text-slate-600"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 rounded-xl overflow-hidden border border-slate-200">
            <MapContainer center={[center.lat, center.lng]} zoom={DEFAULT_ZOOM} scrollWheelZoom className="h-[420px] w-full">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <ClickableMarker value={selected} onChange={onMapPick} />
            </MapContainer>
          </div>

          <div className="space-y-3">
            <p className="text-xs font-black text-slate-500 uppercase tracking-widest">Selected Coordinates</p>
            <input
              className="w-full bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold outline-none"
              value={selected ? Number(selected.lat).toFixed(6) : ""}
              readOnly
              placeholder="Latitude"
            />
            <input
              className="w-full bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold outline-none"
              value={selected ? Number(selected.lng).toFixed(6) : ""}
              readOnly
              placeholder="Longitude"
            />
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 block">Readable Location Name</label>
            <textarea
              className="w-full min-h-[120px] bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-xs font-semibold outline-none"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Human readable place name"
            />
            <p className="text-[11px] text-slate-500 font-semibold">
              Click on map to set location. {isResolving ? "Resolving address..." : "You can edit address manually."}
            </p>
            <button
              type="button"
              className="w-full bg-blue-600 text-white text-xs font-black uppercase tracking-[0.18em] rounded-xl py-3 hover:bg-blue-700 disabled:opacity-60"
              onClick={submit}
              disabled={!selected}
            >
              Use This Location
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
