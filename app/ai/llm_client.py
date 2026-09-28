import json
import re
import requests
from typing import Dict, Any, Optional, List
from app.config.settings import settings
from app.core.logging_config import logger
from app.tools.registry import tool_registry

class LLMClient:
    """Ollama REST API abstraction layer for Qwen 2.5 1.5B supporting multi-step tool action lists."""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = host or settings.ollama_host
        self.model = model or settings.llm_model

    def _call_ollama_generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 256
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json().get("response", "").strip()
            else:
                logger.error(f"Ollama returned HTTP status {res.status_code}: {res.text}")
                return f"Local AI engine error (HTTP {res.status_code})."
        except requests.exceptions.ConnectionError:
            msg = "Your local AI engine (Ollama) is currently unavailable. Please make sure Ollama is running."
            logger.error(msg)
            return msg
        except Exception as e:
            msg = f"LLM generation failed: {e}"
            logger.error(msg)
            return msg

    def process_user_input(
        self,
        user_input: str,
        conversation_context: str = "",
        memory_context: str = ""
    ) -> Dict[str, Any]:
        """
        Analyzes user input independently and determines if one or more tool calls are required.
        Always returns a structured dict maintaining backward compatibility:
        {
            "actions": [ {"tool": "...", "arguments": {...}}, ... ],
            "tool": "first_tool_name" or None,
            "arguments": {...},
            "response": "response text"
        }
        """
        user_input_clean = user_input.strip()

        # 1. First check rule-based intent / greeting / multi-clause override for fast & deterministic classification
        deterministic_intent = self._rule_based_intent_check(user_input_clean)
        if deterministic_intent:
            return deterministic_intent

        # 2. Build system prompt with strict multi-action contract instructions
        tools_list = tool_registry.list_tools()
        tools_json = json.dumps(tools_list, indent=2)

        system_prompt = f"""You are JARVIS, a helpful local Windows personal AI assistant.
Your job is to evaluate the CURRENT USER REQUEST independently and decide whether one or multiple tool actions are required.

AVAILABLE TOOLS SCHEMA:
{tools_json}

MEMORY CONTEXT:
{memory_context}

CRITICAL RULES FOR INTENT SELECTION:
1. Evaluate ONLY the CURRENT USER REQUEST for action selection.
2. DO NOT reuse or repeat tool calls from previous conversation turns unless explicitly requested now.
3. Conversational messages, greetings (e.g. "hello", "hi", "hey"), general knowledge questions, and casual chat MUST have "actions": [].
4. If a user asks for multiple steps (e.g. "open chrome and search youtube for Java DSA"), return MULTIPLE action objects in "actions".
5. Never pass multi-verb sentences as an application name (e.g. "application": "chrome" ONLY, NOT "chrome and search youtube").
6. Output EXACTLY ONE valid JSON object matching one of these two forms:

Form A (Tool Action Sequence):
{{
  "actions": [
    {{ "tool": "<tool_name_1>", "arguments": {{ ... }} }},
    {{ "tool": "<tool_name_2>", "arguments": {{ ... }} }}
  ],
  "response": "<friendly concise summary of what you are doing>"
}}

Form B (Conversational Response):
{{
  "actions": [],
  "response": "<your friendly concise response>"
}}

Output RAW JSON ONLY. No markdown, no extra text."""

        prompt_text = ""
        if conversation_context and conversation_context.strip():
            prompt_text += f"PRIOR CONVERSATION HISTORY (for continuity context only, DO NOT repeat previous tool calls):\n{conversation_context}\n\n"
        prompt_text += f"CURRENT USER REQUEST: {user_input_clean}"

        raw_output = self._call_ollama_generate(prompt_text, system_prompt=system_prompt)
        logger.info(f"Raw LLM Output for '{user_input_clean}': '{raw_output}'")

        parsed = self._extract_json(raw_output)

        # Validate parsed result against LLM contract and tool registry
        if isinstance(parsed, dict):
            actions_list = parsed.get("actions", [])
            resp_val = str(parsed.get("response", "")).strip()

            if not actions_list and parsed.get("tool"):
                t = str(parsed["tool"]).strip()
                if tool_registry.is_registered(t):
                    actions_list = [{"tool": t, "arguments": parsed.get("arguments", {})}]

            valid_actions = []
            for act in actions_list:
                if isinstance(act, dict):
                    t_name = str(act.get("tool", "")).strip()
                    if tool_registry.is_registered(t_name):
                        valid_actions.append({
                            "tool": t_name,
                            "arguments": act.get("arguments", {}) if isinstance(act.get("arguments"), dict) else {}
                        })

            first_tool = valid_actions[0]["tool"] if valid_actions else None
            first_args = valid_actions[0]["arguments"] if valid_actions else {}

            return {
                "actions": valid_actions,
                "tool": first_tool,
                "arguments": first_args,
                "response": resp_val if resp_val else ("Sure, carrying out your request." if valid_actions else "I'm listening. How can I help?")
            }

        clean_text = raw_output.strip().strip('"').strip("`")
        if not clean_text or clean_text.startswith("{") or "tool" in clean_text.lower():
            clean_text = "I'm here. How can I assist you?"

        return {
            "actions": [],
            "tool": None,
            "arguments": {},
            "response": clean_text
        }

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return None

    def _rule_based_intent_check(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Deterministic intent classifier supporting single-clause and multi-clause conjunctions.
        """
        norm_inp = re.sub(r'[^\w\s]', '', user_input.lower()).strip()

        # Pure greetings & simple conversational inputs MUST NOT trigger tool calls
        greetings = {
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "howdy", "greetings", "thanks", "thank you", "who are you",
            "what is your name", "what can you do"
        }
        if norm_inp in greetings:
            return {
                "actions": [],
                "tool": None,
                "arguments": {},
                "response": "Hey! How can I help you today?"
            }

        inp = user_input.lower().strip()

        # Multi-clause splitting logic
        separators = [", then ", " then ", " after that ", " next ", " and "]
        clauses = []
        for sep in separators:
            if sep in inp:
                clauses = [c.strip() for c in inp.split(sep) if c.strip()]
                break

        if not clauses:
            clauses = [inp]

        actions = []
        for clause in clauses:
            single_intent = self._single_clause_intent_check(clause)
            if single_intent and single_intent.get("actions"):
                actions.extend(single_intent["actions"])
            elif single_intent and single_intent.get("tool"):
                actions.append({"tool": single_intent["tool"], "arguments": single_intent.get("arguments", {})})

        if actions:
            resp = "" if len(actions) == 1 else f"Sure! Performing {len(actions)} steps for you."
            first_tool = actions[0]["tool"]
            first_args = actions[0]["arguments"]
            return {
                "actions": actions,
                "tool": first_tool,
                "arguments": first_args,
                "response": resp
            }

        return None

    def _single_clause_intent_check(self, inp: str) -> Optional[Dict[str, Any]]:
        # Dedicated Folder Intent Matching
        if (" folder" in inp or " directory" in inp) and (inp.startswith("open ") or inp.startswith("find ") or inp.startswith("show ") or inp.startswith("launch ")):
            folder_query = inp
            for prefix in ("open ", "find ", "show me ", "show ", "launch "):
                if folder_query.startswith(prefix):
                    folder_query = folder_query[len(prefix):].strip()
                    break
            return {"actions": [{"tool": "find_and_open_folder", "arguments": {"name": folder_query}}]}

        # Direct explicit app matching
        prefixes = ("open ", "launch ", "start ", "show me ")
        for prefix in prefixes:
            if inp.startswith(prefix):
                if inp.startswith("open website") or inp.startswith("open folder"):
                    continue
                if inp.startswith("open file") and not inp.startswith("open file explorer"):
                    continue

                app_name = inp[len(prefix):].strip()
                for noise in (" website", " webiste", " app", " application"):
                    if app_name.endswith(noise):
                        app_name = app_name[:-len(noise)].strip()
                return {"actions": [{"tool": "open_application", "arguments": {"application": app_name}}]}

        # System Metrics
        if inp in ("what is my cpu usage?", "what is my cpu usage", "cpu usage", "get cpu usage", "check cpu", "tell me my cpu usage"):
            return {"actions": [{"tool": "get_cpu_usage", "arguments": {}}]}
        if inp in ("how much ram am i using?", "ram usage", "memory usage", "get memory usage", "check ram"):
            return {"actions": [{"tool": "get_memory_usage", "arguments": {}}]}
        if inp in ("check battery status", "battery status", "battery level", "get battery status"):
            return {"actions": [{"tool": "get_battery_status", "arguments": {}}]}
        if inp in ("get disk usage", "disk usage", "storage usage"):
            return {"actions": [{"tool": "get_disk_usage", "arguments": {}}]}
        if inp in ("system info", "laptop specs", "get system info"):
            return {"actions": [{"tool": "get_system_information", "arguments": {}}]}

        # Web & YouTube
        if inp.startswith("search youtube for "):
            q = inp.replace("search youtube for ", "").strip()
            return {"actions": [{"tool": "search_youtube", "arguments": {"query": q}}]}
        if inp.startswith("search youtube"):
            return {"actions": [{"tool": "search_youtube", "arguments": {"query": ""}}]}
        if inp.startswith("search google for ") or inp.startswith("search web for "):
            q = inp.replace("search google for ", "").replace("search web for ", "").strip()
            return {"actions": [{"tool": "search_web", "arguments": {"query": q}}]}

        # Screenshot / Clipboard
        if inp in ("take screenshot", "capture screen", "take a screenshot"):
            return {"actions": [{"tool": "take_screenshot", "arguments": {}}]}
        if inp in ("read clipboard", "get clipboard"):
            return {"actions": [{"tool": "read_clipboard", "arguments": {}}]}

        # Workflows
        if inp in ("prepare my laptop for coding", "coding mode"):
            return {"actions": [{"tool": "run_preset_workflow", "arguments": {"workflow_name": "coding"}}]}
        if inp in ("dsa study session", "start dsa", "start a 90 minute dsa study session"):
            return {"actions": [{"tool": "run_preset_workflow", "arguments": {"workflow_name": "dsa_study"}}]}

        return None
