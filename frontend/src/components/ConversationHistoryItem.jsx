export default function ConversationHistoryItem({
  id,
  title,
  onSelectConversation,
  isSelected,
}) {
  return (
    <li key={id}>
      <button
        type="button"
        onClick={() => onSelectConversation(id)}
        className={`${isSelected ? "selected" : ""}`}
      >
        {title}
      </button>
    </li>
  );
}
