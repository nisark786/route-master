import ChatWorkspace from "../../components/chat/ChatWorkspace";

export default function CompanyAdministrationChatPage() {
  return (
    <ChatWorkspace
      title="Administration Chat"
      subtitle="Reach platform administrators for support, escalations, and account coordination."
      scope="administration"
      conversationType="ADMINISTRATION"
      emptyContactsLabel="No platform administrators are available for chat right now."
    />
  );
}
