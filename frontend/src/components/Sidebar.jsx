import ConversationHistory from "./ConversationHistory";
import NewConversationButton from "./NewConversationButton";

export default function Sidebar({
  conversations,
  onSelectConversation,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
  selectedConversationId,
}) {
  return (
    <div id="sidebar">
      <NewConversationButton onClick={onNewConversation} />
      <ConversationHistory
        conversations={conversations}
        onSelectConversation={onSelectConversation}
        onRenameConversation={onRenameConversation}
        onDeleteConversation={onDeleteConversation}
        selectedConversationId={selectedConversationId}
      />
    </div>
  );
}
