from backend.storage.repositories import MessageRepository as PackageMessageRepository
from backend.storage.repositories.conversation import MessageRepository as ConversationMessageRepository
from backend.storage.repositories.conversation.message import MessageRepository
from backend.storage.repositories.conversation.message_core import MessageCoreRepository
from backend.storage.repositories.conversation.message_graph import MessageGraphRepository
from backend.storage.repositories.conversation.message_history import MessageHistoryRepository
from backend.storage.repositories.conversation.message_vector import MessageVectorRepository
from backend.storage.repository import MessageRepository as LegacyMessageRepository


def _declared_methods(repository_type: type[object]) -> set[str]:
    return {
        name
        for name, member in vars(repository_type).items()
        if callable(member) and not (name.startswith("__") and name.endswith("__"))
    }


def test_message_repository_imports_resolve_to_compatibility_facade():
    assert PackageMessageRepository is MessageRepository
    assert ConversationMessageRepository is MessageRepository
    assert LegacyMessageRepository is MessageRepository


def test_message_repository_facade_has_focused_non_overlapping_collaborators():
    expected_methods = {
        MessageCoreRepository: {
            "count_dreams_since",
            "delete_message",
            "get_by_id",
            "get_by_ids",
            "get_max_message_id",
            "get_messages_without_metrics",
            "get_messages_without_signatures",
            "get_surprise_index",
            "get_token_totals",
            "increment_message_note_count",
            "insert",
            "mark_message_metabolized",
            "reassign_messages",
            "update_content",
            "update_embedding",
            "update_signature",
        },
        MessageHistoryRepository: {
            "count_messages",
            "get_last_message_timestamp",
            "get_messages_by_conversation",
            "get_messages_since",
            "get_recent",
            "get_recent_assistant_signatures",
            "get_recent_with_metrics",
            "get_recent_with_metrics_for_path",
            "get_sediment_messages_with_metadata",
        },
        MessageVectorRepository: {
            "get_all_embeddings_except",
            "get_embeddings_and_signatures_except",
            "get_embeddings_and_signatures_for_search",
            "get_embeddings_by_speaker",
            "get_embeddings_in_similarity_range",
            "get_glitch_salience_messages",
            "get_last_embedding_by_speaker",
            "get_parallel_messages_by_similarity",
            "get_recent_embeddings",
            "get_structural_signatures_except",
            "search_text",
        },
        MessageGraphRepository: {
            "_normalize_legacy_links",
            "add_message_link",
            "confirm_message_link",
            "delete_message_link",
            "get_ancestor_path",
            "get_message_links",
            "link_exists",
        },
    }

    assert MessageRepository.__bases__ == tuple(expected_methods)
    assert all(_declared_methods(repository_type) == methods for repository_type, methods in expected_methods.items())
    all_methods = [method for methods in expected_methods.values() for method in methods]
    assert len(all_methods) == len(set(all_methods))
    assert all(hasattr(MessageRepository, method) for method in all_methods)
