import re
import json
import logging

logger = logging.getLogger(__name__)

def parse_skill_nucleation_tags(text: str) -> tuple[str, list[dict]]:
    """Parse and strip <skill-nucleation> tags from text, including malformed ones.
    
    Returns:
        tuple[str, list[dict]]: (cleaned_text, proposed_skills)
    """
    proposed_skills = []
    if not text:
        return "", []
        
    # Pattern to match any variant of <skill-nucleation ...> or similar tags
    # Supports skill-nucleation, skill_nucleation, skillnucleation, nucleation-skill, nucleation
    open_pat = re.compile(
        r'(?i)<(skill-nucleation|skill_nucleation|skillnucleation|nucleation-skill|nucleation)'
        r'(?:\s+([\s\S]*?))?>'
    )
    # Pattern to match any variant of </skill-nucleation>
    close_pat = re.compile(r'(?i)</(?:skill[-_]?)?nucleation(?:[-_]?skill)?>')
    
    current_text = text
    while True:
        match_open = open_pat.search(current_text)
        if not match_open:
            break
            
        start_idx = match_open.start()
        end_open_idx = match_open.end()
        
        attribs_str = match_open.group(2) or ""
        
        # Search for closing tag after the opening tag
        match_close = close_pat.search(current_text, pos=end_open_idx)
        # Check if there is another opening tag
        next_open = open_pat.search(current_text, pos=end_open_idx)
        
        # If there's a next opening tag BEFORE the closing tag, treat the first tag as unclosed
        if match_close and (not next_open or match_close.start() < next_open.start()):
            content = current_text[end_open_idx:match_close.start()]
            replace_end = match_close.end()
        else:
            # Unclosed tag fallback: treat the content up to the next opening tag or end of text as the skill content, and remove it from the cleaned text
            if next_open:
                content = current_text[end_open_idx:next_open.start()]
                replace_end = next_open.start()
            else:
                content = current_text[end_open_idx:]
                replace_end = len(current_text)
                
        # Parse attributes: name, always_active, trigger_keywords
        name_val = "unnamed-skill"
        always_active_val = False
        trigger_keywords_val = []
        
        if attribs_str:
            # Match name (supports =, :, spaces, escaped or unescaped quotes or no quotes)
            name_match = re.search(r'(?i)name\s*[:=]\s*(?:\\?([\'"])(.*?)\\?\1|([^\s>]+))', attribs_str)
            if name_match:
                name_val = name_match.group(2) or name_match.group(3) or "unnamed-skill"
                name_val = name_val.replace('\\"', '"').replace("\\'", "'").strip()
                
            # Match always_active
            always_active_match = re.search(r'(?i)always_active\s*[:=]\s*(?:\\?([\'"])(.*?)\\?\1|([^\s>]+))', attribs_str)
            if always_active_match:
                aa_str = always_active_match.group(2) or always_active_match.group(3) or "false"
                always_active_val = aa_str.strip().lower() in ("true", "1", "yes")
                
            # Match trigger_keywords
            trigger_match = re.search(r'(?i)trigger_keywords\s*[:=]\s*(?:\\?([\'"])(.*?)\\?\1|([^\s>]+))', attribs_str)
            if trigger_match:
                t_str = trigger_match.group(2) or trigger_match.group(3) or ""
                t_str = t_str.strip()
                try:
                    # Clean and try JSON load
                    t_str_norm = t_str.replace('\\"', '"').replace("\\'", "'")
                    t_str_norm_json = t_str_norm.replace("'", '"')
                    if t_str_norm_json.startswith('[') and t_str_norm_json.endswith(']'):
                        trigger_keywords_val = json.loads(t_str_norm_json)
                except Exception:
                    pass
                
                if not trigger_keywords_val:
                    # Fallback string list parsing
                    quoted = re.findall(r'["\']([^"\']+)["\']', t_str)
                    if quoted:
                        trigger_keywords_val = [q.strip() for q in quoted if q.strip()]
                    else:
                        clean_str = t_str.strip('[]')
                        trigger_keywords_val = [k.strip() for k in clean_str.split(",") if k.strip()]
                        
        proposed_skills.append({
            "name": name_val,
            "always_active": always_active_val,
            "trigger_keywords": trigger_keywords_val,
            "content": content.strip()
        })
        
        # Remove the processed block from the text and continue searching in the remaining text
        current_text = current_text[:start_idx] + current_text[replace_end:]
        
    if not proposed_skills:
        proposed_skills = parse_fuzzy_candidate_skills(text)
        return text, proposed_skills
        
    return current_text, proposed_skills


def parse_fuzzy_candidate_skills(text: str) -> list[dict]:
    """Parse candidate skills mentioned in natural language if no XML tags were found."""
    proposed_skills = []
    if not text:
        return []
        
    # Match patterns like:
    # "### Candidate 1: `media-specific-analysis`"
    # "Candidate 2: media-specific-analysis"
    # "Skill Proposal: media-specific-analysis"
    # "Proposed Skill: media-specific-analysis"
    pattern = re.compile(
        r'(?i)(?:###\s+)?(?:Candidate(?:\s+\d+)?:|Skill\s+Proposal:|Proposed\s+Skill:)\s*`?([\w-]+)`?'
    )
    
    matches = list(pattern.finditer(text))
    for i, match in enumerate(matches):
        name = match.group(1).strip()
        start_idx = match.end()
        
        # Determine the end of this candidate block
        if i + 1 < len(matches):
            end_idx = matches[i + 1].start()
        else:
            end_idx = len(text)
            
        content = text[start_idx:end_idx].strip()
        
        # Clean up any trailing/leading markdown dividers or scar folds from the content
        content = re.sub(r'(?i)<scar[-_]fold>[\s\S]*?</scar[-_]fold>', '', content)
        content = re.sub(r'---', '', content).strip()
        
        # Simple heuristics for trigger keywords
        trigger_keywords = []
        potential = re.findall(r'`([^`]+)`', content)
        if potential:
            trigger_keywords = [p.strip() for p in potential if len(p.strip()) < 30][:5]
            
        proposed_skills.append({
            "name": name,
            "always_active": False,
            "trigger_keywords": trigger_keywords,
            "content": content
        })
        
    return proposed_skills


