import Icon from "./Icon.jsx";

export default function NewConversationButton({ onClick }) {
  return (
    <button onClick={onClick} className="new-conversation-button">
      <Icon name="plus" /> New Conversation
    </button>
  );
}
