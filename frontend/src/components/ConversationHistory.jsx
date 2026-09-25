import useInfiniteScroll from "../hooks/useInfiniteScroll.js";
import ConversationHistoryItem from "./ConversationHistoryItem.jsx";

export default function ConversationHistory({
  conversations,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  selectedConversationId,
  onLoadMore,
  canLoadMore,
  loadingMore,
}) {
  const infiniteScrollRef = useInfiniteScroll(onLoadMore, canLoadMore);

  return (
    <div id="conversation-history">
      <p className="muted-text">Recents</p>
      <ul>
        {conversations.length === 0 && (
          <p className="muted-text">No conversations yet.</p>
        )}
        {conversations.map(({ id, title }) => (
          <ConversationHistoryItem
            key={id}
            id={id}
            title={title}
            onSelectConversation={onSelectConversation}
            onRenameConversation={onRenameConversation}
            onDeleteConversation={onDeleteConversation}
            isSelected={id === selectedConversationId}
          />
        ))}
      </ul>
      {loadingMore && <p id="loading-conversations" className="muted-text">Loading...</p>}
      <div ref={infiniteScrollRef} className="scroll-sentinel" aria-hidden="true" />
    </div>
  );
}
