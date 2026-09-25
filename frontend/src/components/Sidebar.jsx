import ConversationHistory from "./ConversationHistory";
import NewConversationButton from "./NewConversationButton";

export default function Sidebar({
  conversations,
  onSelectConversation,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
  selectedConversationId,
  onLoadMore,
  canLoadMore,
  loadingMore,
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
        onLoadMore={onLoadMore}
        canLoadMore={canLoadMore}
        loadingMore={loadingMore}
      />
    </div>
  );
}
