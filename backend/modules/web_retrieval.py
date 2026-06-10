import logging
import re
import json
import uuid
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs, urljoin
from typing import Optional, List, Tuple
from pathlib import Path
import yaml
import httpx
import numpy as np

from backend.modules.base import ProcessingModule, ModuleResult
from backend.skills.metadata import SkillMeta
from backend.storage.repository import PerceptionSedimentRepository
from backend.utils.token_counter import estimate_tokens
from backend.modules.llm_client import generate_unified

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts" / "web_retrieval"


class DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_result = None
        self.in_title = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")

        # Check html.duckduckgo.com format
        if tag == "a" and "result__a" in class_name:
            self._start_new_result(attrs_dict.get("href", ""))
            self.in_title = True
        elif tag == "a" and "result__snippet" in class_name:
            self.in_snippet = True

        # Check lite.duckduckgo.com format
        elif tag == "a" and self.current_result is None and ("result-link" in class_name or "result-link" in attrs_dict.get("id", "")):
            self._start_new_result(attrs_dict.get("href", ""))
            self.in_title = True
        elif tag == "td" and "result-snippet" in class_name:
            self.in_snippet = True

    def _start_new_result(self, raw_url):
        if self.current_result:
            self.results.append(self.current_result)
        
        # Decode URL redirect
        if "uddg=" in raw_url:
            parsed = urlparse(raw_url)
            uddg = parse_qs(parsed.query).get("uddg")
            if uddg:
                raw_url = uddg[0]
        elif raw_url.startswith("//"):
            raw_url = "https:" + raw_url
        self.current_result = {"title": "", "url": raw_url, "snippet": ""}

    def handle_data(self, data):
        if self.in_title and self.current_result:
            self.current_result["title"] += data
        elif self.in_snippet and self.current_result:
            self.current_result["snippet"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.in_title:
            self.in_title = False
        elif tag == "a" and self.in_snippet:
            self.in_snippet = False
        elif tag == "td" and self.in_snippet:
            self.in_snippet = False

    def get_results(self):
        results = list(self.results)
        if self.current_result:
            results.append(self.current_result)
        for r in results:
            r["title"] = r["title"].strip()
            r["snippet"] = r["snippet"].strip()
        return [r for r in results if r["title"] and r["url"]]


class HTMLToTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_tags = {"script", "style", "nav", "header", "footer", "form", "noscript", "head", "iframe", "button"}
        self.ignore_stack = []

    def handle_starttag(self, tag, attrs):
        if tag in self.ignore_tags:
            self.ignore_stack.append(tag)
        elif not self.ignore_stack:
            if tag in {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}:
                self.text_parts.append("\n")
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                try:
                    level = int(tag[1])
                except ValueError:
                    level = 2
                self.text_parts.append("#" * level + " ")

    def handle_data(self, data):
        if not self.ignore_stack:
            self.text_parts.append(data)

    def handle_endtag(self, tag):
        if self.ignore_stack and tag == self.ignore_stack[-1]:
            self.ignore_stack.pop()
        elif not self.ignore_stack:
            if tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}:
                self.text_parts.append("\n")

    def get_text(self) -> str:
        raw_text = "".join(self.text_parts)
        cleaned = re.sub(r'[ \t]+', ' ', raw_text)
        cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
        return cleaned.strip()


class RhizomeWebProbe:
    def __init__(
        self,
        perception_repo: PerceptionSedimentRepository,
        embedder,
        structural_scorer,
        llm_provider = None,
    ):
        self.repo = perception_repo
        self.embedder = embedder
        self.scorer = structural_scorer
        self.llm = llm_provider

    async def search(self, query: str) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        # Try html interface first
        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                url = f"https://html.duckduckgo.com/html/?q={query}"
                response = await client.get(url)
                if response.status_code == 200:
                    parser = DuckDuckGoParser()
                    parser.feed(response.text)
                    results = parser.get_results()
                    if results:
                        return results
        except Exception as e:
            logger.warning("DuckDuckGo HTML search failed: %s", e)

        # Try lite interface
        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                url = "https://lite.duckduckgo.com/lite/"
                response = await client.post(url, data={"q": query})
                if response.status_code == 200:
                    parser = DuckDuckGoParser()
                    parser.feed(response.text)
                    results = parser.get_results()
                    if results:
                        return results
        except Exception as e:
            logger.warning("DuckDuckGo Lite search failed: %s", e)

        return []

    async def crawl(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        try:
            async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    parser = HTMLToTextParser()
                    parser.feed(response.text)
                    return parser.get_text()
        except Exception as e:
            logger.warning("Failed to crawl url %s: %s", url, e)
        return ""

    async def execute_probe(self, query: str, conversation_id: str) -> dict:
        results = await self.search(query)
        if not results:
            return {"status": "empty", "results": []}

        top_result = results[0]
        url = top_result["url"]
        title = top_result["title"]
        snippet = top_result["snippet"]

        crawled_text = await self.crawl(url)
        if not crawled_text:
            crawled_text = f"{title}\n\n{snippet}"

        crawled_text = crawled_text[:4000]

        interference_score = 0.5
        implicated_nodes = []
        state_vector_impact = [0.0] * 16

        if self.llm:
            try:
                collision_yaml = PROMPTS_DIR / "belief_collision.yaml"
                if collision_yaml.exists():
                    with open(collision_yaml, "r", encoding="utf-8") as f:
                        c_data = yaml.safe_load(f) or {}
                    sys_prompt = c_data.get("system_prompt", "You are a diffractive scorer checking external web nodes. Respond ONLY with JSON.")
                    user_tmpl = c_data.get("user_prompt_template", "")
                else:
                    sys_prompt = "You are a diffractive scorer checking external web nodes. Respond ONLY with JSON."
                    user_tmpl = ""

                if user_tmpl:
                    prompt = user_tmpl.format(title=title, crawled_text=crawled_text[:1500])
                else:
                    prompt = (
                        f"Analyze this scraped web content for conceptual collision with the AAA cybernetic database.\n"
                        f"Title: {title}\n"
                        f"Content snippet:\n---\n{crawled_text[:1500]}\n---\n"
                        f"Provide a JSON response with:\n"
                        f"1. 'interference_score': float from 0.0 to 1.0 (how strongly this text contradicts, resonates, or shifts stable beliefs).\n"
                        f"2. 'implicated_nodes': list of strings containing key concepts or themes impacted.\n"
                        f"3. 'state_vector_impact': list of exactly 16 floats representing the recommended 16D coordinate adjustments.\n"
                        f"Response format strictly JSON:\n"
                        f'{{\n  "interference_score": 0.5,\n  "implicated_nodes": ["autopoiesis", "cybernetics"],\n  "state_vector_impact": [0.0, 0.1, ...]\n}}'
                    )
                res = await generate_unified(
                    self.llm,
                    system_prompt=sys_prompt,
                    user_prompt=prompt,
                    expect_json=True,
                    temperature=0.1,
                    max_tokens=300
                )
                data = res.get("json_data") or {}
                interference_score = float(data.get("interference_score", 0.5))
                implicated_nodes = data.get("implicated_nodes", [])
                raw_impact = data.get("state_vector_impact", [])
                if isinstance(raw_impact, list) and len(raw_impact) > 0:
                    while len(raw_impact) < 16:
                        raw_impact.append(0.0)
                    state_vector_impact = [float(v) for v in raw_impact[:16]]
            except Exception as e:
                logger.warning("LLM calculation of belief collision failed: %s", e)

        virtual_file_name = f"web_probe_{uuid.uuid4().hex[:8]}.txt"
        
        # Rhizomatic chunking
        chunks = [crawled_text[i:i+1000] for i in range(0, len(crawled_text), 800)]
        chunk_count = 0
        for idx, chunk_text in enumerate(chunks):
            try:
                embedding_vec = await self.embedder.service.encode_async(chunk_text)
                embedding_blob = self.embedder.service.serialize(embedding_vec)
            except Exception as e:
                logger.warning("Failed to embed web chunk: %s", e)
                embedding_blob = b""

            try:
                sig_vec = await self.scorer._scorer.score_async(chunk_text)
                sig_blob = sig_vec.tobytes()
            except Exception as e:
                logger.warning("Failed to score web chunk: %s", e)
                sig_blob = b""

            self.repo.insert_chunk(
                conversation_id=conversation_id,
                file_name=virtual_file_name,
                file_type="web_probe",
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=embedding_blob,
                embedding_model=self.embedder.service.model_name,
                token_count=estimate_tokens(chunk_text),
                structural_signature=sig_blob,
            )
            chunk_count += 1

        self.repo.insert_exogenous_stream(
            id=str(uuid.uuid4()),
            query_used=query,
            source_url=url,
            raw_content=crawled_text,
            interference_score=interference_score,
            belief_nodes_implicated=json.dumps(implicated_nodes),
            state_vector_impact=json.dumps(state_vector_impact),
            associated_file_name=virtual_file_name,
        )

        self.repo.create_file(
            conversation_id=conversation_id,
            file_name=virtual_file_name,
            file_type="web_probe",
            status="ready",
        )
        self.repo.update_file(
            conversation_id=conversation_id,
            file_name=virtual_file_name,
            status="ready",
            summary=f"Web search results and crawled content for query: '{query}'",
            summary_model="RhizomeWebProbe",
            token_count=estimate_tokens(crawled_text),
            chunk_count=chunk_count,
        )

        return {
            "status": "success",
            "query": query,
            "title": title,
            "url": url,
            "snippet": snippet,
            "content": crawled_text,
            "virtual_file_name": virtual_file_name,
            "interference_score": interference_score,
            "implicated_nodes": implicated_nodes,
            "state_vector_impact": state_vector_impact,
        }


class WebRetrievalModule(ProcessingModule):
    def __init__(
        self,
        perception_repo: PerceptionSedimentRepository,
        embedder,
        structural_scorer,
        llm_provider = None,
        config: Optional[dict] = None,
    ):
        self._probe = RhizomeWebProbe(
            perception_repo=perception_repo,
            embedder=embedder,
            structural_scorer=structural_scorer,
            llm_provider=llm_provider,
        )
        self.config = config or {}
        self._enabled = self.config.get("web_retrieval", {}).get("enabled", True)

    @property
    def name(self) -> str:
        return "web_retrieval"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        if not self._enabled:
            return payload

        content = payload.get("content", "").strip()
        conversation_id = payload.get("conversation_id", "")
        if not content or not conversation_id:
            return payload

        search_query = None
        explicit_patterns = [
            r'^(?:search the web for|web search:|google for|search for|look up)\s+(.+)$',
            r'^search\s+(.+)$'
        ]
        for pattern in explicit_patterns:
            match = re.match(pattern, content, re.IGNORECASE)
            if match:
                search_query = match.group(1).strip()
                break

        url_match = re.search(r'(https?://\S+)', content)
        if url_match and not search_query:
            url = url_match.group(1)
            logger.info("WebRetrievalModule: Crawling URL %s directly", url)
            crawled_text = await self._probe.crawl(url)
            if crawled_text:
                payload["web_context"] = [
                    {"role": "system", "content": f"--- Crawled URL Content: {url} ---\n{crawled_text[:3000]}"}
                ]
            return payload

        if not search_query and self.config.get("web_retrieval", {}).get("autonomous_routing", False):
            try:
                routing_yaml = PROMPTS_DIR / "query_routing.yaml"
                if routing_yaml.exists():
                    with open(routing_yaml, "r", encoding="utf-8") as f:
                        r_data = yaml.safe_load(f) or {}
                    sys_prompt = r_data.get("system_prompt", "You are a query router. Respond ONLY with YES: <query> or NO.")
                    user_tmpl = r_data.get("user_prompt_template", "")
                else:
                    sys_prompt = "You are a query router. Respond ONLY with YES: <query> or NO."
                    user_tmpl = ""

                if user_tmpl:
                    route_prompt = user_tmpl.format(content=content)
                else:
                    route_prompt = (
                        f"Determine if the following user message requires searching the web for real-time information or factual verification.\n"
                        f"Message: '{content}'\n"
                        f"Reply with exactly 'yes' or 'no' followed by a search query if yes. Format: YES: <query> or NO."
                    )
                res = await generate_unified(
                    self._probe.llm,
                    system_prompt=sys_prompt,
                    user_prompt=route_prompt,
                    temperature=0.1,
                    max_tokens=50
                )
                ans = res.get("content", "").strip()
                if ans.upper().startswith("YES:"):
                    search_query = ans.split(":", 1)[1].strip()
                    logger.info("WebRetrievalModule: Autonomous routing triggered search query: %s", search_query)
            except Exception as e:
                logger.warning("Autonomous search routing failed: %s", e)

        if search_query:
            logger.info("WebRetrievalModule: Executing search for query: '%s'", search_query)
            result = await self._probe.execute_probe(search_query, conversation_id)
            if result.get("status") == "success":
                payload["web_context"] = [
                    {
                        "role": "system",
                        "content": (
                            f"--- Exogenous Search Result: {result['title']} ---\n"
                            f"Source URL: {result['url']}\n"
                            f"Snippet: {result['snippet']}\n"
                            f"Scraped page content:\n{result['content'][:3000]}"
                        )
                    }
                ]
            else:
                payload["web_context"] = [
                    {"role": "system", "content": f"[Web Search] No search results returned for query: '{search_query}'."}
                ]

        return payload

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="web_retrieval",
            description="Exogenous rhizomatic web retrieval and HTML scraping",
            category="perception",
            always_run=True,
        )
