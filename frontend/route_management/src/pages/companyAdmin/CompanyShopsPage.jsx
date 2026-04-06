import { useEffect, useMemo, useState } from "react";
import { ImagePlus, MapPin, Pencil, Plus, Save, Search, Store, Trash2 } from "lucide-react";
import { toast } from "react-toastify";
import {
  useCreateShopMutation,
  useCreateMediaUploadUrlMutation,
  useDeleteShopMutation,
  useGetShopsQuery,
  useResetShopOwnerPasswordMutation,
  useUpdateShopMutation,
} from "../../features/companyAdmin/companyAdminApi";
import MapLocationPickerModal from "../../components/companyAdmin/MapLocationPickerModal";
import LocationPreviewMap from "../../components/companyAdmin/LocationPreviewMap";
import { extractApiErrorMessage, extractApiSuccessMessage } from "../../utils/adminUi";
import { getRuntimeConfig } from "../../config/runtimeConfig";
import AdminModal from "../../components/companyAdmin/AdminModal";

const INITIAL_SHOP_DRAFT = {
  name: "",
  owner_name: "",
  owner_mobile_number: "",
  temporary_password: "",
  location: "",
  location_display_name: "",
  latitude: "",
  longitude: "",
  address: "",
  landmark: "",
  image: null,
};

const API_BASE_URL = getRuntimeConfig("VITE_API_URL", import.meta.env.VITE_API_URL || "/api/");
const DIRECT_MEDIA_UPLOAD_ENABLED = getRuntimeConfig("VITE_DIRECT_MEDIA_UPLOAD", "true").toLowerCase() === "true";
const MAX_IMAGE_DIMENSION = 1600;
const RESIZE_THRESHOLD_BYTES = 300 * 1024;

const toMediaUrl = (value) => {
  if (!value) return "";
  if (!/^https?:\/\//i.test(value) && !value.startsWith("/")) {
    value = `/media/${String(value).replace(/^\/+/, "")}`;
  }
  const apiOrigin = new URL(API_BASE_URL, window.location.origin).origin;
  const url = new URL(value, apiOrigin);
  if (url.hostname === window.location.hostname && !url.port && window.location.port) {
    url.host = window.location.host;
  }
  if (url.hostname === "backend" || url.hostname === "route_backend") {
    url.host = window.location.host;
  }
  return url.toString();
};

const validateImageFile = (file) => {
  if (!(file instanceof File)) return null;
  if (!file.type?.startsWith("image/")) {
    return "Please choose a valid image file.";
  }
  if (file.size > 5 * 1024 * 1024) {
    return "Image size must be 5MB or less.";
  }
  return null;
};

const resizeImageIfNeeded = async (file) => {
  if (!(file instanceof File) || file.size <= RESIZE_THRESHOLD_BYTES) {
    return file;
  }

  const imageBitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_IMAGE_DIMENSION / Math.max(imageBitmap.width, imageBitmap.height));
  if (scale === 1) {
    imageBitmap.close();
    return file;
  }

  const canvas = document.createElement("canvas");
  canvas.width = Math.round(imageBitmap.width * scale);
  canvas.height = Math.round(imageBitmap.height * scale);
  const context = canvas.getContext("2d");
  context.drawImage(imageBitmap, 0, 0, canvas.width, canvas.height);
  imageBitmap.close();

  const mimeType = file.type?.startsWith("image/") ? file.type : "image/jpeg";
  const quality = mimeType === "image/png" ? undefined : 0.82;
  const blob = await new Promise((resolve) => {
    canvas.toBlob((nextBlob) => resolve(nextBlob), mimeType, quality);
  });

  if (!blob || blob.size >= file.size) {
    return file;
  }
  return new File([blob], file.name, { type: mimeType, lastModified: Date.now() });
};

export default function CompanyShopsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useGetShopsQuery({ search, page });
  const [createShop, { isLoading: isCreating, error: createError }] = useCreateShopMutation();
  const [createMediaUploadUrl] = useCreateMediaUploadUrlMutation();
  const [updateShop, { isLoading: isUpdating, error: updateError }] = useUpdateShopMutation();
  const [deleteShop, { isLoading: isDeleting, error: deleteError }] = useDeleteShopMutation();
  const [resetShopOwnerPassword, { isLoading: isResettingPassword, error: resetPasswordError }] = useResetShopOwnerPasswordMutation();

  const [draft, setDraft] = useState(INITIAL_SHOP_DRAFT);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState(INITIAL_SHOP_DRAFT);
  const [editExistingImageUrl, setEditExistingImageUrl] = useState("");
  const [confirmAction, setConfirmAction] = useState(null);
  const [mapTarget, setMapTarget] = useState(null);
  const [resetTargetShopId, setResetTargetShopId] = useState(null);
  const [resetTempPassword, setResetTempPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [displayShops, setDisplayShops] = useState([]);

  const shops = useMemo(() => data?.results || [], [data?.results]);
  const totalPages = data?.total_pages || 1;

  useEffect(() => {
    setDisplayShops(shops);
  }, [shops]);

  const feedback = useMemo(
    () =>
      extractApiErrorMessage(error) ||
      extractApiErrorMessage(createError) ||
      extractApiErrorMessage(updateError) ||
      extractApiErrorMessage(deleteError) ||
      extractApiErrorMessage(resetPasswordError),
    [error, createError, updateError, deleteError, resetPasswordError]
  );

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `shops-error-${feedback}` });
    }
  }, [feedback]);

  const createPreviewUrl = useMemo(
    () => (draft.image instanceof File ? URL.createObjectURL(draft.image) : ""),
    [draft.image]
  );
  const editSelectedPreviewUrl = useMemo(
    () => (editDraft.image instanceof File ? URL.createObjectURL(editDraft.image) : ""),
    [editDraft.image]
  );

  useEffect(() => () => {
    if (createPreviewUrl) URL.revokeObjectURL(createPreviewUrl);
  }, [createPreviewUrl]);

  useEffect(() => () => {
    if (editSelectedPreviewUrl) URL.revokeObjectURL(editSelectedPreviewUrl);
  }, [editSelectedPreviewUrl]);

  const uploadImageAsset = async (file) => {
    if (!(file instanceof File)) {
      return {};
    }

    const validationMessage = validateImageFile(file);
    if (validationMessage) {
      throw new Error(validationMessage);
    }

    let optimizedFile = file;
    try {
      optimizedFile = await resizeImageIfNeeded(file);
      if (!DIRECT_MEDIA_UPLOAD_ENABLED) {
        return { image: optimizedFile };
      }

      const uploadPayload = await createMediaUploadUrl({
        kind: "shop",
        file_name: optimizedFile.name,
        content_type: optimizedFile.type || "image/jpeg",
        file_size: optimizedFile.size,
      }).unwrap();

      const uploadResponse = await fetch(uploadPayload.upload_url, {
        method: uploadPayload.method || "PUT",
        headers: uploadPayload.headers || { "Content-Type": optimizedFile.type || "image/jpeg" },
        body: optimizedFile,
      });

      if (!uploadResponse.ok) {
        throw new Error("Direct upload failed.");
      }

      return { image_key: uploadPayload.object_key, image: null };
    } catch (error) {
      if (error?.message === "Please choose a valid image file." || error?.message === "Image size must be 5MB or less.") {
        throw error;
      }
      return { image: optimizedFile };
    }
  };

  const getEntityId = (payload) => payload?.id || payload?.data?.id || "";

  const onSearch = (e) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const attachImageInBackground = async (shopId, file) => {
    try {
      const imagePayload = await uploadImageAsset(file);
      const updated = await updateShop({
        shopId,
        body: {
          image: imagePayload.image ?? null,
          image_key: imagePayload.image_key ?? "",
        },
      }).unwrap();
      if (updated?.id) {
        setDisplayShops((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      }
      toast.success("Shop image uploaded.");
    } catch (error) {
      toast.warning(error?.message || "Shop created, but image upload failed.");
    }
  };

  const onCreateShop = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const imageFile = draft.image instanceof File ? draft.image : null;
      const payload = {
        ...draft,
        image: null,
        image_key: "",
        latitude: Number(draft.latitude),
        longitude: Number(draft.longitude),
      };
      if (String(payload.owner_mobile_number || "").trim() && !String(payload.temporary_password || "").trim()) {
        toast.error("Temporary password is required when owner mobile number is provided.");
        return;
      }
      const created = await createShop({
        ...payload,
      }).unwrap();
      const shopId = getEntityId(created);
      if (shopId) {
        setDisplayShops((prev) => [created, ...prev.filter((item) => item.id !== shopId)]);
      }
      const successMessage = extractApiSuccessMessage(created);
      if (successMessage) toast.success(successMessage);
      setDraft(INITIAL_SHOP_DRAFT);
      setPage(1);
      setIsCreateOpen(false);
      if (imageFile && shopId) {
        void attachImageInBackground(shopId, imageFile);
      }
    } catch (error) {
      if (error?.message) {
        toast.error(error.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const startEdit = (shop) => {
    setEditingId(shop.id);
    setEditDraft({
      name: shop.name || "",
      owner_name: shop.owner_name || "",
      owner_mobile_number: shop.owner_mobile_number || "",
      temporary_password: "",
      location: shop.location || "",
      location_display_name: shop.location_display_name || "",
      latitude: shop.latitude ?? "",
      longitude: shop.longitude ?? "",
      address: shop.address || "",
      landmark: shop.landmark || "",
      image: null,
    });
    setEditExistingImageUrl(shop.image || "");
  };

  const saveEdit = (e) => {
    e.preventDefault();
    if (!editingId) return;
    if (String(editDraft.owner_mobile_number || "").trim() && !String(editDraft.temporary_password || "").trim()) {
      toast.error("Temporary password is required when owner mobile number is provided.");
      return;
    }
    setConfirmAction({ type: "update", shopId: editingId });
  };

  const removeShop = (shopId) => setConfirmAction({ type: "delete", shopId });

  const onConfirmAction = async () => {
    if (!confirmAction) return;
    setIsSubmitting(true);
    try {
      if (confirmAction.type === "delete") {
        const response = await deleteShop(confirmAction.shopId).unwrap();
        setDisplayShops((prev) => prev.filter((item) => item.id !== confirmAction.shopId));
        const successMessage = extractApiSuccessMessage(response);
        if (successMessage) toast.success(successMessage);
        if (editingId === confirmAction.shopId) {
          setEditingId(null);
          setEditExistingImageUrl("");
        }
      }
      if (confirmAction.type === "update") {
        const imagePayload = await uploadImageAsset(editDraft.image);
        const updated = await updateShop({
          shopId: confirmAction.shopId,
          body: {
            ...editDraft,
            ...imagePayload,
            latitude: Number(editDraft.latitude),
            longitude: Number(editDraft.longitude),
          },
        }).unwrap();
        if (updated?.id) {
          setDisplayShops((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
        }
        const successMessage = extractApiSuccessMessage(updated);
        if (successMessage) toast.success(successMessage);
        setEditingId(null);
        setEditExistingImageUrl("");
      }
      setConfirmAction(null);
    } catch (error) {
      if (confirmAction.type === "delete" && Number(error?.status) === 404) {
        toast.info("Shop already deleted.");
        await refetch();
        setConfirmAction(null);
        return;
      }
      if (error?.message) {
        toast.error(error.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const openMapPicker = (target) => setMapTarget(target);

  const onResetPassword = async () => {
    if (!resetTargetShopId) return;
    try {
      const payload = { temporary_password: resetTempPassword.trim() };
      const response = await resetShopOwnerPassword({ shopId: resetTargetShopId, body: payload }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setResetTargetShopId(null);
      setResetTempPassword("");
    } catch {
      // Mutation error is handled from query state.
    }
  };

  const applyPickedLocation = (payload) => {
    if (mapTarget === "create") {
      setDraft((prev) => ({
        ...prev,
        ...payload,
      }));
    }
    if (mapTarget === "edit") {
      setEditDraft((prev) => ({
        ...prev,
        ...payload,
      }));
    }
    setMapTarget(null);
  };

  const mapInitialValue = mapTarget === "edit"
    ? (editDraft.latitude && editDraft.longitude
      ? { lat: Number(editDraft.latitude), lng: Number(editDraft.longitude) }
      : null)
    : (draft.latitude && draft.longitude
      ? { lat: Number(draft.latitude), lng: Number(draft.longitude) }
      : null);

  const mapInitialDisplayName = mapTarget === "edit" ? editDraft.location_display_name : draft.location_display_name;

  return (
    <div className="space-y-8 p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">Shop Management</h1>
        <p className="text-slate-500 font-medium mt-1">Create and manage shops with map-based location selection.</p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700"
          onClick={() => setIsCreateOpen(true)}
        >
          <Plus size={14} /> Add Shop
        </button>
      </div>

      <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-8 border-b border-slate-100 bg-slate-50/50 space-y-4">
            <div>
              <h2 className="text-lg font-black text-slate-900 tracking-tight">Shops</h2>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Search by shop or owner name</p>
            </div>
            <form className="flex gap-2" onSubmit={onSearch}>
              <div className="relative flex-1">
                <Search size={14} className="absolute top-1/2 -translate-y-1/2 left-3 text-slate-400" />
                <input
                  className="w-full bg-white border border-slate-200 rounded-xl px-9 py-2.5 text-sm font-semibold outline-none"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search by name or owner..."
                />
              </div>
              <button
                type="submit"
                className="px-4 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest hover:bg-black"
              >
                Search
              </button>
            </form>
          </div>

          {isLoading ? (
            <p className="p-8 text-sm text-slate-500">Loading shops...</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {displayShops.map((shop) => (
                <div key={shop.id} className="p-6 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                        <Store size={18} />
                      </div>
                      <div>
                        <p className="text-sm font-black text-slate-900">{shop.name}</p>
                        <p className="text-[11px] font-bold text-slate-500">Owner: {shop.owner_name}</p>
                        <p className="text-[11px] font-semibold text-slate-500">
                          Owner mobile: {shop.owner_mobile_number || "-"}
                        </p>
                        <p className="text-[11px] font-semibold text-slate-500 inline-flex items-center gap-1 mt-1">
                          <MapPin size={12} /> {shop.location_display_name || shop.location || "No location"}
                        </p>
                      </div>
                    </div>
                    {shop.image ? (
                      <img src={toMediaUrl(shop.image)} alt={shop.name} className="h-14 w-20 rounded-lg object-cover border border-slate-200" />
                    ) : (
                      <div className="h-14 w-20 rounded-lg bg-slate-100 border border-slate-200 text-slate-400 flex items-center justify-center">
                        <ImagePlus size={16} />
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-600 font-semibold">
                    <p>Latitude: {shop.latitude}</p>
                    <p>Longitude: {shop.longitude}</p>
                    <p>Address: {shop.address || "-"}</p>
                    <p>Landmark: {shop.landmark || "-"}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-blue-100 text-blue-600 hover:bg-blue-50 transition-all inline-flex items-center gap-1"
                      onClick={() => startEdit(shop)}
                      disabled={isUpdating || isSubmitting}
                    >
                      <Pencil size={12} /> Edit
                    </button>
                    <button
                      type="button"
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-rose-100 text-rose-600 hover:bg-rose-50 transition-all inline-flex items-center gap-1"
                      onClick={() => removeShop(shop.id)}
                      disabled={isDeleting || isSubmitting}
                    >
                      <Trash2 size={12} /> Delete
                    </button>
                    <button
                      type="button"
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-amber-200 text-amber-700 hover:bg-amber-50 transition-all inline-flex items-center gap-1 disabled:opacity-50"
                      onClick={() => {
                        setResetTargetShopId(shop.id);
                        setResetTempPassword("");
                      }}
                      disabled={isResettingPassword || !shop.owner_user_id}
                      title={shop.owner_user_id ? "Reset owner password" : "Owner account not created"}
                    >
                      Reset Password
                    </button>
                  </div>
                </div>
              ))}

              {!displayShops.length ? <p className="p-8 text-sm text-slate-500">No shops found.</p> : null}
            </div>
          )}

          <div className="p-6 border-t border-slate-100 flex items-center justify-between">
            <p className="text-xs font-bold text-slate-500">
              Page {data?.page || 1} of {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-700 disabled:opacity-40"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={(data?.page || 1) <= 1 || isLoading}
              >
                Previous
              </button>
              <button
                type="button"
                className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-700 disabled:opacity-40"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={(data?.page || 1) >= totalPages || isLoading}
              >
                Next
              </button>
            </div>
          </div>
      </div>

      <AdminModal
        isOpen={isCreateOpen}
        title="Add Shop"
        description="Create a shop and pick its location from the map."
        onClose={() => setIsCreateOpen(false)}
      >
        <form className="space-y-4" onSubmit={onCreateShop}>
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.name}
            onChange={(e) => setDraft((p) => ({ ...p, name: e.target.value }))}
            placeholder="Shop Name"
            required
          />
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.owner_name}
            onChange={(e) => setDraft((p) => ({ ...p, owner_name: e.target.value }))}
            placeholder="Owner Name"
            required
          />
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.owner_mobile_number}
            onChange={(e) => setDraft((p) => ({ ...p, owner_mobile_number: e.target.value }))}
            placeholder="Owner Mobile Number (optional)"
          />
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.temporary_password}
            onChange={(e) => setDraft((p) => ({ ...p, temporary_password: e.target.value }))}
            placeholder="Owner Temporary Password"
          />

          <div className="space-y-2">
            <label className="ml-1 block text-[10px] font-black uppercase tracking-widest text-slate-400">Map Location</label>
            <button
              type="button"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100"
              onClick={() => openMapPicker("create")}
            >
              {draft.location_display_name || "Pick location on map"}
            </button>
            <div className="grid grid-cols-2 gap-2">
              <input className="rounded-xl border-slate-200 bg-slate-50 px-3 py-2.5 text-xs font-bold outline-none" value={draft.latitude} placeholder="Latitude" readOnly />
              <input className="rounded-xl border-slate-200 bg-slate-50 px-3 py-2.5 text-xs font-bold outline-none" value={draft.longitude} placeholder="Longitude" readOnly />
            </div>
            <LocationPreviewMap latitude={draft.latitude} longitude={draft.longitude} />
          </div>

          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.address}
            onChange={(e) => setDraft((p) => ({ ...p, address: e.target.value }))}
            placeholder="Address"
          />
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.landmark}
            onChange={(e) => setDraft((p) => ({ ...p, landmark: e.target.value }))}
            placeholder="Landmark"
          />

          <label className="block">
            <span className="ml-1 text-[10px] font-black uppercase tracking-widest text-slate-400">Shop Image</span>
            <input
              type="file"
              accept="image/*"
              className="mt-1 block w-full text-xs font-bold text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-slate-700"
              onChange={(e) => setDraft((p) => ({ ...p, image: e.target.files?.[0] || null }))}
            />
          </label>

          {createPreviewUrl ? (
            <img src={createPreviewUrl} alt="Selected shop preview" className="h-24 w-full rounded-xl border border-slate-200 object-cover" />
          ) : null}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => setIsCreateOpen(false)}
              disabled={isCreating || isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white disabled:opacity-60"
              disabled={isCreating || isSubmitting || !draft.latitude || !draft.longitude}
            >
              {isCreating || isSubmitting ? "Saving..." : "Create Shop"}
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        isOpen={!!editingId}
        title="Edit Shop"
        description="Update shop details and location."
        onClose={() => {
          setEditingId(null);
          setEditExistingImageUrl("");
        }}
      >
        <form className="space-y-4" onSubmit={saveEdit}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.name}
              onChange={(e) => setEditDraft((p) => ({ ...p, name: e.target.value }))}
              placeholder="Shop Name"
              required
            />
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.owner_name}
              onChange={(e) => setEditDraft((p) => ({ ...p, owner_name: e.target.value }))}
              placeholder="Owner Name"
              required
            />
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.owner_mobile_number}
              onChange={(e) => setEditDraft((p) => ({ ...p, owner_mobile_number: e.target.value }))}
              placeholder="Owner Mobile Number (optional)"
            />
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.temporary_password}
              onChange={(e) => setEditDraft((p) => ({ ...p, temporary_password: e.target.value }))}
              placeholder="Owner Temporary Password"
            />
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100"
              onClick={() => openMapPicker("edit")}
            >
              {editDraft.location_display_name || "Pick location on map"}
            </button>
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.latitude}
              readOnly
              placeholder="Latitude"
              required
            />
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.longitude}
              readOnly
              placeholder="Longitude"
              required
            />
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.landmark}
              onChange={(e) => setEditDraft((p) => ({ ...p, landmark: e.target.value }))}
              placeholder="Landmark"
            />
          </div>

          <div>
            <LocationPreviewMap latitude={editDraft.latitude} longitude={editDraft.longitude} />
          </div>

          <textarea
            className="w-full min-h-[90px] rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={editDraft.address}
            onChange={(e) => setEditDraft((p) => ({ ...p, address: e.target.value }))}
            placeholder="Address"
          />

          <label className="block">
            <span className="ml-1 text-[10px] font-black uppercase tracking-widest text-slate-400">Update Image (optional)</span>
            <input
              type="file"
              accept="image/*"
              className="mt-1 block w-full text-xs font-bold text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-slate-700"
              onChange={(e) => setEditDraft((p) => ({ ...p, image: e.target.files?.[0] || null }))}
            />
          </label>
          {editSelectedPreviewUrl || editExistingImageUrl ? (
            <img
              src={editSelectedPreviewUrl || toMediaUrl(editExistingImageUrl)}
              alt="Shop image preview"
              className="h-24 w-full rounded-xl border border-slate-200 object-cover"
            />
          ) : null}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => {
                setEditingId(null);
                setEditExistingImageUrl("");
              }}
              disabled={isUpdating || isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white transition-all hover:bg-black disabled:opacity-60"
              disabled={isUpdating || isSubmitting || !editDraft.latitude || !editDraft.longitude}
            >
              <Save size={14} /> {isUpdating || isSubmitting ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </AdminModal>

      {confirmAction ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">
              {confirmAction.type === "delete" ? "Confirm Delete" : "Confirm Update"}
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              {confirmAction.type === "delete"
                ? "Are you sure you want to delete this shop? This action cannot be undone."
                : "Are you sure you want to update this shop details?"}
            </p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => setConfirmAction(null)}
                disabled={isDeleting || isUpdating || isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`px-4 py-2 rounded-xl text-white text-xs font-black uppercase tracking-widest disabled:opacity-60 ${
                  confirmAction.type === "delete" ? "bg-rose-600 hover:bg-rose-700" : "bg-slate-900 hover:bg-black"
                }`}
                onClick={onConfirmAction}
                disabled={isDeleting || isUpdating || isSubmitting}
              >
                {confirmAction.type === "delete"
                  ? isDeleting || isSubmitting
                    ? "Deleting..."
                    : "OK, Delete"
                  : isUpdating || isSubmitting
                    ? "Saving..."
                    : "OK, Update"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <MapLocationPickerModal
        isOpen={!!mapTarget}
        initialValue={mapInitialValue}
        initialDisplayName={mapInitialDisplayName}
        onClose={() => setMapTarget(null)}
        onConfirm={applyPickedLocation}
      />

      {resetTargetShopId ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">Reset Shop Owner Password</h3>
            <p className="mt-2 text-sm text-slate-600">
              Set a temporary password. Owner will be forced to change password at next login.
            </p>
            <input
              className="mt-4 w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
              value={resetTempPassword}
              onChange={(e) => setResetTempPassword(e.target.value)}
              placeholder="Temporary Password"
            />
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => {
                  setResetTargetShopId(null);
                  setResetTempPassword("");
                }}
                disabled={isResettingPassword}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-black uppercase tracking-widest disabled:opacity-60"
                onClick={onResetPassword}
                disabled={isResettingPassword}
              >
                {isResettingPassword ? "Resetting..." : "Reset"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
