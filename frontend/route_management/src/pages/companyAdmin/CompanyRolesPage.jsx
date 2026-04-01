import { useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";
import {
  useAssignRbacRoleToUserMutation,
  useCreateRbacRoleMutation,
  useDeleteRbacAssignmentMutation,
  useDeleteRbacRoleMutation,
  useGetRbacAssignmentsQuery,
  useGetRbacPermissionsQuery,
  useGetRbacRolesQuery,
  useUpdateRbacRoleMutation,
} from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage } from "../../utils/adminUi";
import AdminModal from "../../components/companyAdmin/AdminModal";

const INITIAL_ROLE = { code: "", name: "", description: "", permission_codes: [] };
const INITIAL_ASSIGN = { user_id: "", role_id: "" };

const togglePermissionCode = (draft, code) => {
  const exists = draft.permission_codes.includes(code);
  return {
    ...draft,
    permission_codes: exists
      ? draft.permission_codes.filter((item) => item !== code)
      : [...draft.permission_codes, code],
  };
};

export default function CompanyRolesPage() {
  const { data: permissions = [], error: permissionsError } = useGetRbacPermissionsQuery();
  const { data: roles = [], error: rolesError } = useGetRbacRolesQuery();
  const { data: assignmentsPayload = {}, error: assignmentsError } = useGetRbacAssignmentsQuery();
  const [createRole, { isLoading: isCreatingRole, error: createRoleError }] = useCreateRbacRoleMutation();
  const [updateRole, { isLoading: isUpdatingRole, error: updateRoleError }] = useUpdateRbacRoleMutation();
  const [deleteRole, { isLoading: isDeletingRole }] = useDeleteRbacRoleMutation();
  const [assignRole, { isLoading: isAssigningRole, error: assignRoleError }] = useAssignRbacRoleToUserMutation();
  const [deleteAssignment, { isLoading: isDeletingAssignment }] = useDeleteRbacAssignmentMutation();

  const [isCreateRoleOpen, setIsCreateRoleOpen] = useState(false);
  const [isAssignRoleOpen, setIsAssignRoleOpen] = useState(false);
  const [roleDraft, setRoleDraft] = useState(INITIAL_ROLE);
  const [editingRoleId, setEditingRoleId] = useState(null);
  const [editRoleDraft, setEditRoleDraft] = useState(INITIAL_ROLE);
  const [assignDraft, setAssignDraft] = useState(INITIAL_ASSIGN);
  const [confirmAction, setConfirmAction] = useState(null);

  const feedback = useMemo(
    () =>
      extractApiErrorMessage(permissionsError) ||
      extractApiErrorMessage(rolesError) ||
      extractApiErrorMessage(assignmentsError) ||
      extractApiErrorMessage(createRoleError) ||
      extractApiErrorMessage(updateRoleError) ||
      extractApiErrorMessage(assignRoleError),
    [permissionsError, rolesError, assignmentsError, createRoleError, updateRoleError, assignRoleError]
  );

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `rbac-feedback-${feedback}` });
    }
  }, [feedback]);

  const assignments = assignmentsPayload.assignments || [];
  const users = assignmentsPayload.users || [];

  const onCreateRole = async (event) => {
    event.preventDefault();
    try {
      await createRole(roleDraft).unwrap();
      toast.success("Role created successfully.");
      setRoleDraft(INITIAL_ROLE);
      setIsCreateRoleOpen(false);
    } catch {
      // handled by mutation state
    }
  };

  const startEditRole = (role) => {
    setEditingRoleId(role.id);
    setEditRoleDraft({
      code: role.code || "",
      name: role.name || "",
      description: role.description || "",
      permission_codes: role.permission_codes || role.permissions?.map((permission) => permission.code) || [],
    });
  };

  const onSaveRole = async (event) => {
    event.preventDefault();
    if (!editingRoleId) return;
    try {
      await updateRole({ roleId: editingRoleId, body: editRoleDraft }).unwrap();
      toast.success("Role updated successfully.");
      setEditingRoleId(null);
    } catch {
      // handled by mutation state
    }
  };

  const onAssignRole = async (event) => {
    event.preventDefault();
    try {
      await assignRole(assignDraft).unwrap();
      toast.success("Role assigned successfully.");
      setAssignDraft(INITIAL_ASSIGN);
      setIsAssignRoleOpen(false);
    } catch {
      // handled by mutation state
    }
  };

  const onDeleteConfirmed = async () => {
    if (!confirmAction) return;
    try {
      if (confirmAction.type === "role") {
        await deleteRole(confirmAction.id).unwrap();
        toast.success("Role deleted.");
      }
      if (confirmAction.type === "assignment") {
        await deleteAssignment(confirmAction.id).unwrap();
        toast.success("Assignment removed.");
      }
      setConfirmAction(null);
    } catch {
      // handled by mutation state
    }
  };

  return (
    <div className="space-y-8 p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Role & Permission Management</h1>
          <p className="text-slate-500 font-medium mt-1">Create custom roles and assign permission codes to company users.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-widest text-slate-700 hover:bg-slate-50"
            onClick={() => setIsAssignRoleOpen(true)}
          >
            Assign Role
          </button>
          <button
            type="button"
            className="rounded-xl bg-blue-600 px-4 py-3 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700"
            onClick={() => setIsCreateRoleOpen(true)}
          >
            Add Role
          </button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-lg font-black text-slate-900">Roles</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {roles.map((role) => (
            <div key={role.id} className="px-6 py-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-black text-slate-900">{role.name}</p>
                <p className="text-xs text-slate-500">{role.code}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="px-3 py-2 rounded-xl border border-blue-200 text-blue-600 text-xs font-bold"
                  onClick={() => startEditRole(role)}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="px-3 py-2 rounded-xl border border-rose-200 text-rose-600 text-xs font-bold disabled:opacity-50"
                  onClick={() => setConfirmAction({ type: "role", id: role.id })}
                  disabled={role.is_system}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          {!roles.length ? <p className="p-6 text-sm text-slate-500">No roles available.</p> : null}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-lg font-black text-slate-900">User Role Assignments</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {assignments.map((assignment) => (
            <div key={assignment.id} className="px-6 py-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-black text-slate-900">{assignment.user_email || assignment.user_mobile_number}</p>
                <p className="text-xs text-slate-500">
                  {assignment.role_name} ({assignment.role_code})
                </p>
              </div>
              <button
                type="button"
                className="px-3 py-2 rounded-xl border border-rose-200 text-rose-600 text-xs font-bold"
                onClick={() => setConfirmAction({ type: "assignment", id: assignment.id })}
              >
                Remove
              </button>
            </div>
          ))}
          {!assignments.length ? <p className="p-6 text-sm text-slate-500">No assignments available.</p> : null}
        </div>
      </div>

      <AdminModal
        isOpen={isCreateRoleOpen}
        title="Create Role"
        description="Define a reusable permission set for company users."
        onClose={() => setIsCreateRoleOpen(false)}
      >
        <form onSubmit={onCreateRole} className="space-y-4">
          <input
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm"
            placeholder="Role Code (e.g. route_operator)"
            value={roleDraft.code}
            onChange={(e) => setRoleDraft((prev) => ({ ...prev, code: e.target.value }))}
            required
          />
          <input
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm"
            placeholder="Role Name"
            value={roleDraft.name}
            onChange={(e) => setRoleDraft((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
          <textarea
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm min-h-20"
            placeholder="Description (optional)"
            value={roleDraft.description}
            onChange={(e) => setRoleDraft((prev) => ({ ...prev, description: e.target.value }))}
          />
          <div className="space-y-2 max-h-56 overflow-auto border border-slate-100 rounded-xl p-3">
            {permissions.map((permission) => (
              <label key={permission.code} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={roleDraft.permission_codes.includes(permission.code)}
                  onChange={() => setRoleDraft((prev) => togglePermissionCode(prev, permission.code))}
                />
                <span>{permission.code}</span>
              </label>
            ))}
          </div>
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => setIsCreateRoleOpen(false)}
              disabled={isCreatingRole}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white disabled:opacity-50"
              disabled={isCreatingRole}
            >
              {isCreatingRole ? "Creating..." : "Create Role"}
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        isOpen={!!editingRoleId}
        title="Edit Role"
        description="Update role details and permission codes."
        onClose={() => setEditingRoleId(null)}
      >
        <form onSubmit={onSaveRole} className="space-y-4">
          <input
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm"
            placeholder="Role Code"
            value={editRoleDraft.code}
            onChange={(e) => setEditRoleDraft((prev) => ({ ...prev, code: e.target.value }))}
            required
          />
          <input
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm"
            placeholder="Role Name"
            value={editRoleDraft.name}
            onChange={(e) => setEditRoleDraft((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
          <textarea
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm min-h-20"
            placeholder="Description (optional)"
            value={editRoleDraft.description}
            onChange={(e) => setEditRoleDraft((prev) => ({ ...prev, description: e.target.value }))}
          />
          <div className="space-y-2 max-h-56 overflow-auto border border-slate-100 rounded-xl p-3">
            {permissions.map((permission) => (
              <label key={permission.code} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={editRoleDraft.permission_codes.includes(permission.code)}
                  onChange={() => setEditRoleDraft((prev) => togglePermissionCode(prev, permission.code))}
                />
                <span>{permission.code}</span>
              </label>
            ))}
          </div>
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => setEditingRoleId(null)}
              disabled={isUpdatingRole}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white disabled:opacity-50"
              disabled={isUpdatingRole}
            >
              {isUpdatingRole ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        isOpen={isAssignRoleOpen}
        title="Assign Role To User"
        description="Pick a user and attach one of your company roles."
        onClose={() => setIsAssignRoleOpen(false)}
      >
        <form onSubmit={onAssignRole} className="space-y-4">
          <select
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm"
            value={assignDraft.user_id}
            onChange={(e) => setAssignDraft((prev) => ({ ...prev, user_id: e.target.value }))}
            required
          >
            <option value="">Select user</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.email || user.mobile_number || user.id}
              </option>
            ))}
          </select>
          <select
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm"
            value={assignDraft.role_id}
            onChange={(e) => setAssignDraft((prev) => ({ ...prev, role_id: e.target.value }))}
            required
          >
            <option value="">Select role</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name} ({role.code})
              </option>
            ))}
          </select>
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => setIsAssignRoleOpen(false)}
              disabled={isAssigningRole}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white disabled:opacity-50"
              disabled={isAssigningRole}
            >
              {isAssigningRole ? "Assigning..." : "Assign Role"}
            </button>
          </div>
        </form>
      </AdminModal>

      {confirmAction ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">
              {confirmAction.type === "role" ? "Delete Role" : "Remove Assignment"}
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              {confirmAction.type === "role"
                ? "Are you sure you want to delete this role?"
                : "Are you sure you want to remove this user role assignment?"}
            </p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => setConfirmAction(null)}
                disabled={isDeletingRole || isDeletingAssignment}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-black uppercase tracking-widest disabled:opacity-60"
                onClick={onDeleteConfirmed}
                disabled={isDeletingRole || isDeletingAssignment}
              >
                {isDeletingRole || isDeletingAssignment ? "Working..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
