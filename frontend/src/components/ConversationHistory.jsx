import ConversationHistoryItem from "./ConversationHistoryItem.jsx";

export default function ConversationHistory({
  conversations,
  onSelectConversation,
  selectedConversationId,
}) {
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
            isSelected={id === selectedConversationId}
          />
        ))}
      </ul>
    </div>
  );
}
