import ConversationHistory from "./ConversationHistory";
import NewConversationButton from "./NewConversationButton";

export default function Sidebar({
  conversations,
  onSelectConversation,
  onNewConversation,
  selectedConversationId,
}) {
  return (
    <div id="sidebar">
      <NewConversationButton onClick={onNewConversation} />
      <ConversationHistory
        conversations={conversations}
        onSelectConversation={onSelectConversation}
        selectedConversationId={selectedConversationId}
      />
    </div>
  );
}
