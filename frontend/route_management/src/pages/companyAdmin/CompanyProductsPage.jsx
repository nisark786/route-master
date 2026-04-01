import { useEffect, useMemo, useState } from "react";
import { Box, ImagePlus, PackagePlus, Pencil, Save, Trash2 } from "lucide-react";
import { toast } from "react-toastify";
import {
  useCreateProductMutation,
  useCreateMediaUploadUrlMutation,
  useDeleteProductMutation,
  useGetProductsQuery,
  useUpdateProductMutation,
} from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage, extractApiSuccessMessage } from "../../utils/adminUi";
import { getRuntimeConfig } from "../../config/runtimeConfig";
import AdminModal from "../../components/companyAdmin/AdminModal";

const createInitialDraft = () => ({
  name: "",
  image: null,
  quantity_count: "",
  rate: "",
  description: "",
  shelf_life: "",
});

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

export default function CompanyProductsPage() {
  const { data: products = [], isLoading, error, refetch } = useGetProductsQuery();
  const [createProduct, { isLoading: isCreating, error: createError }] = useCreateProductMutation();
  const [createMediaUploadUrl] = useCreateMediaUploadUrlMutation();
  const [updateProduct, { isLoading: isUpdating, error: updateError }] = useUpdateProductMutation();
  const [deleteProduct, { isLoading: isDeleting, error: deleteError }] = useDeleteProductMutation();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [displayProducts, setDisplayProducts] = useState([]);
  const [draft, setDraft] = useState(createInitialDraft);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState(INITIAL_DRAFT);
  const [editExistingImageUrl, setEditExistingImageUrl] = useState("");
  const [confirmAction, setConfirmAction] = useState(null);

  const feedback = useMemo(
    () =>
      extractApiErrorMessage(error) ||
      extractApiErrorMessage(createError) ||
      extractApiErrorMessage(updateError) ||
      extractApiErrorMessage(deleteError),
    [error, createError, updateError, deleteError]
  );

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `products-error-${feedback}` });
    }
  }, [feedback]);

  useEffect(() => {
    setDisplayProducts(products);
  }, [products]);

  const createPreviewUrl = useMemo(
    () => (draft.image instanceof File ? URL.createObjectURL(draft.image) : ""),
    [draft.image]
  );
  const editSelectedPreviewUrl = useMemo(
    () => (editDraft.image instanceof File ? URL.createObjectURL(editDraft.image) : ""),
    [editDraft.image]
  );

  useEffect(
    () => () => {
      if (createPreviewUrl) URL.revokeObjectURL(createPreviewUrl);
    },
    [createPreviewUrl]
  );

  useEffect(
    () => () => {
      if (editSelectedPreviewUrl) URL.revokeObjectURL(editSelectedPreviewUrl);
    },
    [editSelectedPreviewUrl]
  );

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
        kind: "product",
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

  const attachImageInBackground = async (productId, file) => {
    try {
      const imagePayload = await uploadImageAsset(file);
      const response = await updateProduct({
        productId,
        body: {
          image: imagePayload.image ?? null,
          image_key: imagePayload.image_key ?? "",
        },
      }).unwrap();
      if (response?.id) {
        setDisplayProducts((prev) => prev.map((item) => (item.id === response.id ? response : item)));
      }
      toast.success("Product image uploaded.");
    } catch (error) {
      const message = error?.message || "Product created, but image upload failed.";
      toast.warning(message);
    }
  };

  const onCreate = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      const imageFile = draft.image instanceof File ? draft.image : null;
      const response = await createProduct({
        ...draft,
        image: null,
        image_key: "",
        quantity_count: Number(draft.quantity_count || 0),
        rate: Number(draft.rate || 0),
      }).unwrap();
      const productId = getEntityId(response);
      if (productId) {
        setDisplayProducts((prev) => [response, ...prev.filter((item) => item.id !== productId)]);
      }
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setDraft(createInitialDraft());
      setIsCreateOpen(false);
      if (imageFile && productId) {
        void attachImageInBackground(productId, imageFile);
      }
    } catch (error) {
      if (error?.message) {
        toast.error(error.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const startEdit = (product) => {
    setEditingId(product.id);
    setEditDraft({
      name: product.name || "",
      image: null,
      quantity_count: product.quantity_count ?? 0,
      rate: product.rate ?? 0,
      description: product.description || "",
      shelf_life: product.shelf_life || "",
    });
    setEditExistingImageUrl(product.image || "");
  };

  const onSaveEdit = (event) => {
    event.preventDefault();
    if (!editingId) return;
    setConfirmAction({ type: "update", productId: editingId });
  };

  const onDelete = (productId) => {
    setConfirmAction({ type: "delete", productId });
  };

  const onConfirmAction = async () => {
    if (!confirmAction) return;
    setIsSubmitting(true);
    try {
      if (confirmAction.type === "delete") {
        const response = await deleteProduct(confirmAction.productId).unwrap();
        setDisplayProducts((prev) => prev.filter((item) => item.id !== confirmAction.productId));
        const successMessage = extractApiSuccessMessage(response);
        if (successMessage) toast.success(successMessage);
      }

      if (confirmAction.type === "update") {
        const imagePayload = await uploadImageAsset(editDraft.image);
        const response = await updateProduct({
          productId: confirmAction.productId,
          body: {
            ...editDraft,
            ...imagePayload,
            quantity_count: Number(editDraft.quantity_count || 0),
            rate: Number(editDraft.rate || 0),
          },
        }).unwrap();
        if (response?.id) {
          setDisplayProducts((prev) => prev.map((item) => (item.id === response.id ? response : item)));
        }
        const successMessage = extractApiSuccessMessage(response);
        if (successMessage) toast.success(successMessage);
        setEditingId(null);
        setEditExistingImageUrl("");
      }

      setConfirmAction(null);
    } catch (error) {
      if (confirmAction.type === "delete" && Number(error?.status) === 404) {
        toast.info("Product already deleted.");
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

  return (
    <div className="space-y-8 p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-slate-900">Product Management</h1>
          <p className="mt-1 font-medium text-slate-500">Add, update, and remove company products.</p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700"
          onClick={() => {
            setDraft(createInitialDraft());
            setIsCreateOpen(true);
          }}
        >
          <PackagePlus size={14} /> Add Product
        </button>
      </div>

      <div className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 bg-slate-50/50 p-8">
          <h2 className="text-lg font-black tracking-tight text-slate-900">Products</h2>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Current company product catalog</p>
        </div>

        {isLoading ? (
          <p className="p-8 text-sm text-slate-500">Loading products...</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {displayProducts.map((product) => (
              <div key={product.id} className="space-y-4 p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                      <Box size={18} />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-black text-slate-900">{product.name}</p>
                      <p className="text-xs font-semibold text-slate-600">
                        Qty: {product.quantity_count} | Rate: {product.rate}
                      </p>
                      <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                        Shelf life: {product.shelf_life || "-"}
                      </p>
                    </div>
                  </div>
                  {product.image ? (
                    <img
                      src={toMediaUrl(product.image)}
                      alt={product.name}
                      className="h-14 w-20 rounded-lg border border-slate-200 object-cover"
                    />
                  ) : (
                    <div className="flex h-14 w-20 items-center justify-center rounded-lg border border-slate-200 bg-slate-100 text-slate-400">
                      <ImagePlus size={16} />
                    </div>
                  )}
                </div>

                <p className="text-xs font-medium text-slate-600">{product.description || "No description."}</p>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-xl border border-blue-100 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-blue-600 transition-all hover:bg-blue-50"
                    onClick={() => startEdit(product)}
                    disabled={isUpdating || isSubmitting}
                  >
                    <Pencil size={12} /> Edit
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-xl border border-rose-100 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-rose-600 transition-all hover:bg-rose-50"
                    onClick={() => onDelete(product.id)}
                    disabled={isDeleting || isSubmitting}
                  >
                    <Trash2 size={12} /> Delete
                  </button>
                </div>
              </div>
            ))}
            {!displayProducts.length ? <p className="p-8 text-sm text-slate-500">No products added yet.</p> : null}
          </div>
        )}
      </div>

      <AdminModal
        isOpen={isCreateOpen}
        title="Add Product"
        description="Create a new product in your catalog."
        onClose={() => {
          setDraft(createInitialDraft());
          setIsCreateOpen(false);
        }}
      >
        <form className="space-y-4" onSubmit={onCreate}>
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.name}
            onChange={(event) => setDraft((prev) => ({ ...prev, name: event.target.value }))}
            placeholder="Product Name"
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="number"
              min={0}
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={draft.quantity_count}
              onChange={(event) => setDraft((prev) => ({ ...prev, quantity_count: event.target.value }))}
              placeholder="Quantity"
              required
            />
            <input
              type="number"
              min={0}
              step="0.01"
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={draft.rate}
              onChange={(event) => setDraft((prev) => ({ ...prev, rate: event.target.value }))}
              placeholder="Rate"
              required
            />
          </div>
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.shelf_life}
            onChange={(event) => setDraft((prev) => ({ ...prev, shelf_life: event.target.value }))}
            placeholder="Shelf Life (e.g. 3 months)"
          />
          <textarea
            className="min-h-[90px] w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.description}
            onChange={(event) => setDraft((prev) => ({ ...prev, description: event.target.value }))}
            placeholder="Description"
          />

          <label className="block">
            <span className="ml-1 text-[10px] font-black uppercase tracking-widest text-slate-400">Product Image</span>
            <input
              type="file"
              accept="image/*"
              className="mt-1 block w-full text-xs font-bold text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-slate-700"
              onChange={(event) => setDraft((prev) => ({ ...prev, image: event.target.files?.[0] || null }))}
            />
          </label>

          {createPreviewUrl ? (
            <img src={createPreviewUrl} alt="Product preview" className="h-24 w-full rounded-xl border border-slate-200 object-cover" />
          ) : null}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => {
                setDraft(createInitialDraft());
                setIsCreateOpen(false);
              }}
              disabled={isCreating || isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white transition-all hover:bg-black disabled:opacity-60"
              disabled={isCreating || isSubmitting}
            >
              {isCreating || isSubmitting ? "Saving..." : "Create Product"}
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        isOpen={!!editingId}
        title="Edit Product"
        description="Update product details."
        onClose={() => {
          setEditingId(null);
          setEditExistingImageUrl("");
        }}
      >
        <form className="space-y-4" onSubmit={onSaveEdit}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.name}
              onChange={(event) => setEditDraft((prev) => ({ ...prev, name: event.target.value }))}
              placeholder="Product Name"
              required
            />
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.shelf_life}
              onChange={(event) => setEditDraft((prev) => ({ ...prev, shelf_life: event.target.value }))}
              placeholder="Shelf Life"
            />
            <input
              type="number"
              min={0}
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.quantity_count}
              onChange={(event) => setEditDraft((prev) => ({ ...prev, quantity_count: event.target.value }))}
              placeholder="Quantity"
              required
            />
            <input
              type="number"
              min={0}
              step="0.01"
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.rate}
              onChange={(event) => setEditDraft((prev) => ({ ...prev, rate: event.target.value }))}
              placeholder="Rate"
              required
            />
          </div>

          <textarea
            className="min-h-[90px] w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={editDraft.description}
            onChange={(event) => setEditDraft((prev) => ({ ...prev, description: event.target.value }))}
            placeholder="Description"
          />

          <label className="block">
            <span className="ml-1 text-[10px] font-black uppercase tracking-widest text-slate-400">Update Image (optional)</span>
            <input
              type="file"
              accept="image/*"
              className="mt-1 block w-full text-xs font-bold text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-slate-700"
              onChange={(event) => setEditDraft((prev) => ({ ...prev, image: event.target.files?.[0] || null }))}
            />
          </label>

          {editSelectedPreviewUrl || editExistingImageUrl ? (
            <img
              src={editSelectedPreviewUrl || toMediaUrl(editExistingImageUrl)}
              alt="Product preview"
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
              disabled={isUpdating || isSubmitting}
            >
              <Save size={14} /> {isUpdating || isSubmitting ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </AdminModal>

      {confirmAction ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[1px]">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <h3 className="text-base font-black text-slate-900">
              {confirmAction.type === "delete" ? "Confirm Delete" : "Confirm Update"}
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              {confirmAction.type === "delete"
                ? "Are you sure you want to delete this product?"
                : "Are you sure you want to update this product details?"}
            </p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
                onClick={() => setConfirmAction(null)}
                disabled={isDeleting || isUpdating || isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`rounded-xl px-4 py-2 text-xs font-black uppercase tracking-widest text-white disabled:opacity-60 ${
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
    </div>
  );
}
