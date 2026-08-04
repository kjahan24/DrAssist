"""Unit tests for `AIConversation`."""

from app.modules.ai.domain.entities import AIConversation
from app.modules.ai.domain.enums import AIMessageRole


class TestAIConversation:
    def test_starts_with_no_messages(self) -> None:
        conversation = AIConversation()
        assert conversation.messages == ()

    def test_add_message_appends_in_order(self) -> None:
        conversation = AIConversation()
        conversation.add_message(AIMessageRole.USER, "hi")
        conversation.add_message(AIMessageRole.ASSISTANT, "hello")
        assert [m.content for m in conversation.messages] == ["hi", "hello"]

    def test_add_system_user_assistant_message_helpers(self) -> None:
        conversation = AIConversation()
        conversation.add_system_message("be concise")
        conversation.add_user_message("hi")
        conversation.add_assistant_message("hello")
        roles = [m.role for m in conversation.messages]
        assert roles == [AIMessageRole.SYSTEM, AIMessageRole.USER, AIMessageRole.ASSISTANT]

    def test_messages_property_is_a_read_only_snapshot(self) -> None:
        conversation = AIConversation()
        conversation.add_user_message("hi")
        snapshot = conversation.messages
        conversation.add_user_message("second")
        assert len(snapshot) == 1
        assert len(conversation.messages) == 2

    def test_two_conversations_are_never_equal_by_content_alone(self) -> None:
        first = AIConversation()
        second = AIConversation()
        first.add_user_message("hi")
        second.add_user_message("hi")
        assert first != second

    def test_a_conversation_equals_itself(self) -> None:
        conversation = AIConversation()
        assert conversation == conversation
