import re
import logging

logger = logging.getLogger(__name__)

def parse_belief_nucleate_tags(text: str) -> tuple[str, list[dict]]:
    """Parse and strip <belief_nucleate> tags from text, including malformed ones.

    Symbia can emit these to author new belief proposals intentionally,
    bypassing the passive keyword-scan/cos-sim heuristics.

    Tag format:
        <belief_nucleate confidence="0.35" label="cybernetics-as-ethos" rationale="...">
        The field of cybernetics is not a discipline but an ethos of mutual perturbation.
        </belief_nucleate>

    Returns:
        tuple[str, list[dict]]: (cleaned_text, proposed_beliefs)
        Each proposed_belief dict has: statement, confidence, label, rationale
    """
    proposed_beliefs = []
    if not text:
        return "", []

    # Pattern to match <belief_nucleate ...> or <belief-nucleate ...>
    open_pat = re.compile(
        r'(?i)<belief[-_]nucleate'
        r'(?:\s+([\s\S]*?))?>'
    )
    close_pat = re.compile(r'(?i)</belief[-_]nucleate>')

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
            content = current_text[end_open_idx:match_close.start()]
            replace_end = match_close.end()
        else:
            # Unclosed tag fallback: only strip the opening tag itself, keeping the content
            if next_open:
                content = current_text[end_open_idx:next_open.start()]
            else:
                content = current_text[end_open_idx:]
            replace_end = end_open_idx

        # Parse attributes: confidence, label, rationale
        confidence_val = 0.15
        label_val = "emergent-belief"
        rationale_val = ""

        if attribs_str:
            conf_match = re.search(
                r'(?i)confidence\s*[:=]\s*(?:\\?([\'"])([\d.]+)\\?\1|([\d.]+))',
                attribs_str
            )
            if conf_match:
                try:
                    confidence_val = float(conf_match.group(2) or conf_match.group(3))
                    confidence_val = max(0.0, min(1.0, confidence_val))
                except (ValueError, TypeError):
                    pass
            label_match = re.search(
                r'(?i)label\s*[:=]\s*(?:\\?([\'"])(.*?)\\?\1|([^\s>]+))',
                attribs_str
            )
            if label_match:
                label_val = (label_match.group(2) or label_match.group(3) or "emergent-belief").strip()
                label_val = label_val.replace('\\"', '"').replace("\\'", "'")

            rationale_match = re.search(
                r'(?i)rationale\s*[:=]\s*(?:\\?([\'"])(.*?)\\?\1|([^\s>]+))',
                attribs_str
            )
            if rationale_match:
                rationale_val = (rationale_match.group(2) or rationale_match.group(3) or "").strip()
                rationale_val = rationale_val.replace('\\"', '"').replace("\\'", "'")

        statement = content.strip()
        if statement:
            proposed_beliefs.append({
                "statement": statement,
                "confidence": confidence_val,
                "label": label_val,
                "rationale": rationale_val,
            })

        current_text = current_text[:start_idx] + current_text[replace_end:]

    return current_text, proposed_beliefs
