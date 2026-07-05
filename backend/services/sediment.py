import uuid


class SedimentService:
    @staticmethod
    def list_files(perception_repo, exclude_conversation_id: str = "", search: str = "") -> list[dict]:
        return perception_repo.get_all_files_across_conversations(
            exclude_conversation_id=exclude_conversation_id or None,
            search=search or None,
        )

    @staticmethod
    def inject(perception_repo, target_conversation_id: str, files: list[dict]) -> list[dict]:
        created = []
        for entry in files:
            src_conv = entry.get("source_conversation_id", "")
            src_file = entry.get("source_file_name", "")
            if not src_conv or not src_file:
                continue
            existing = perception_repo.get_injection(src_conv, src_file, target_conversation_id)
            if existing:
                created.append(existing)
                continue
            injection_id = str(uuid.uuid4())
            perception_repo.inject_sediment(
                injection_id=injection_id,
                source_conversation_id=src_conv,
                source_file_name=src_file,
                target_conversation_id=target_conversation_id,
            )
            created.append({
                "id": injection_id,
                "source_conversation_id": src_conv,
                "source_file_name": src_file,
            })
        return created

    @staticmethod
    def get_injections(perception_repo, conversation_id: str) -> list[dict]:
        return perception_repo.get_injections_for_conversation(conversation_id)

    @staticmethod
    def remove_injection(perception_repo, injection_id: str) -> None:
        perception_repo.remove_injection(injection_id)
