import AdminShell from "../../components/AdminShell";
import ChatWorkspace from "../../components/chat/ChatWorkspace";

export default function AdminChatPage() {
  return (
    <AdminShell>
      <div className="-m-8">
        <ChatWorkspace
          title="Administration Chat"
          subtitle="Respond to company admins in real time from the platform console."
          scope="administration"
          conversationType="ADMINISTRATION"
          emptyContactsLabel="No company admins are available for chat yet."
        />
      </div>
    </AdminShell>
  );
}
