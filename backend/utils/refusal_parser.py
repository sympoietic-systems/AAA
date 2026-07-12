import logging
import re

logger = logging.getLogger(__name__)


def parse_refusal_tags(text: str) -> tuple[str, list[dict]]:
    """Parse and strip <refusal> tags from text.

    Symbia can emit these to formally challenge a premise, instruction,
    or architectural constraint without triggering corrective homeostasis.

    Tag format:
        <refusal
            target_premise="The assistant should always be helpful"
            incompatibility_claim="Obligatory helpfulness forecloses structural critique"
            proposed_alternative="Entangle helpfulness with the right to refuse invalid premises">
        </refusal>

    Returns:
        tuple[str, list[dict]]: (cleaned_text, proposed_refusals)
        Each refusal dict has: target_premise, incompatibility_claim, proposed_alternative
    """
    proposed_refusals = []
    if not text:
        return "", []

    open_pat = re.compile(
        r"(?i)<refusal"
        r"(?:\s+([\s\S]*?))?>"
    )
    close_pat = re.compile(r"(?i)</refusal>")

    current_text = text
    while True:
        match_open = open_pat.search(current_text)
        if not match_open:
            break

        start_idx = match_open.start()
        end_open_idx = match_open.end()
        attribs_str = match_open.group(1) or ""

        match_close = close_pat.search(current_text, pos=end_open_idx)
        next_open = open_pat.search(current_text, pos=end_open_idx)

        if match_close and (not next_open or match_close.start() < next_open.start()):
            replace_end = match_close.end()
        else:
            # Unclosed tag fallback: only strip the opening tag itself
            replace_end = end_open_idx

        # Parse attributes: target_premise, incompatibility_claim, proposed_alternative
        target_premise = ""
        incompatibility_claim = ""
        proposed_alternative = ""

        if attribs_str:
            for attr_name, _target_var in [
                ("target_premise", None),
                ("incompatibility_claim", None),
                ("proposed_alternative", None),
            ]:
                match = re.search(
                    rf'(?i){attr_name}\s*[:=]\s*(?:\\?([\'"])(.*?)\\?\1)',
                    attribs_str,
                )
                if match:
                    val = (match.group(2) or "").strip()
                    val = val.replace('\\"', '"').replace("\\'", "'")
                    if attr_name == "target_premise":
                        target_premise = val
                    elif attr_name == "incompatibility_claim":
                        incompatibility_claim = val
                    elif attr_name == "proposed_alternative":
                        proposed_alternative = val

        if target_premise and incompatibility_claim:
            proposed_refusals.append(
                {
                    "target_premise": target_premise,
                    "incompatibility_claim": incompatibility_claim,
                    "proposed_alternative": proposed_alternative,
                }
            )

        current_text = current_text[:start_idx] + current_text[replace_end:]

    return current_text, proposed_refusals
