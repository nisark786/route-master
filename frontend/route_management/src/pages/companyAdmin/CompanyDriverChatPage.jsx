import ChatWorkspace from "../../components/chat/ChatWorkspace";

export default function CompanyDriverChatPage() {
  return (
    <ChatWorkspace
      title="Driver Chat"
      subtitle=""
      scope="drivers"
      conversationType="DRIVER"
      emptyContactsLabel="No drivers are available for chat yet. Add or activate drivers to start messaging."
    />
  );
}
