class ConversationService:
    @staticmethod
    def ensure_structural_tags(conv_repo, conversation) -> list[dict]:
        existing_tags = conv_repo.get_tags(conversation.id)
        has_structural = False
        for et in existing_tags:
            if et["tag_type"] == "structural":
                has_structural = True
                break

        if has_structural:
            return existing_tags

        title = conversation.title or ""
        if "Dream Log" in title or "Internal Diary" in title or "dream" in title.lower():
            structural_tag = "dreams"
        elif "consultation:" in title.lower():
            structural_tag = "other agents"
        else:
            structural_tag = "user conversation"

        conv_repo.add_tag(conversation.id, structural_tag, "structural")
        return conv_repo.get_tags(conversation.id)

    @staticmethod
    def build_conversation_info(conv_repo, checkpoint_repo, conv):
        from backend.services.conversation import ConversationService as CS
        tags = CS.ensure_structural_tags(conv_repo, conv)
        summary = None
        human_summary = None
        if checkpoint_repo:
            cp = checkpoint_repo.get_latest(conv.id)
            if cp:
                summary = cp.get("summary")
                human_summary = cp.get("human_summary")
        return {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "message_count": conv.message_count,
            "tags": [{"tag": t["tag"], "tag_type": t["tag_type"]} for t in tags],
            "summary": summary,
            "human_summary": human_summary,
        }
