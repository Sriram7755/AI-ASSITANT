import re
import json
import datetime
from typing import Dict, Any, Optional, List
from app.brain.prompts import SYSTEM_PROMPT_TEMPLATE
from app.brain.ollama_client import OllamaClient
from app.tools.registry import tool_registry
from app.core.logging_config import logger

class IntentParser:
    """Parses natural language requests into structured action sequences for HP using deterministic rule routing + Ollama."""

    VALID_APP_NAMES = {
        "chrome", "google chrome", "vscode", "visual studio code", "code",
        "notepad", "spotify", "calculator", "calc", "settings", "ms-settings",
        "file explorer", "explorer", "cmd", "command prompt", "terminal",
        "powershell", "word", "excel", "powerpoint", "browser", "edge", "vlc",
        "task manager", "control panel", "device manager"
    }

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()

    def parse(self, user_input: str, conversation_context: str = "", memory_context: str = "") -> Dict[str, Any]:
        user_input_clean = user_input.strip()

        # 1. Deterministic Rule-Based Check (Fast, Safe & Reliable)
        rule_intent = self._rule_based_check(user_input_clean)
        if rule_intent:
            return rule_intent

        # 2. Ollama Prompting
        tools_list = tool_registry.list_tools()
        tools_json = json.dumps(tools_list, indent=2)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tools_json=tools_json, memory_context=memory_context)

        prompt_text = ""
        if conversation_context and conversation_context.strip():
            prompt_text += f"PRIOR CONVERSATION HISTORY:\n{conversation_context}\n\n"
        prompt_text += f"CURRENT USER REQUEST: {user_input_clean}"

        raw_output = self.ollama.generate(prompt_text, system_prompt=system_prompt)
        logger.info(f"Raw LLM Output for '{user_input_clean}': '{raw_output}'")

        parsed = self._extract_json(raw_output)

        if isinstance(parsed, dict):
            intent_type = parsed.get("intent", "CONVERSATION")
            actions_list = parsed.get("actions", [])
            resp_val = str(parsed.get("response", "")).strip()

            if intent_type in ("CONVERSATION", "CLARIFICATION_REQUIRED", "SYSTEM_INFORMATION"):
                if not actions_list:
                    actions_list = []

            if not actions_list and parsed.get("tool") and intent_type not in ("CONVERSATION", "CLARIFICATION_REQUIRED"):
                t = str(parsed["tool"]).strip()
                if tool_registry.is_registered(t):
                    actions_list = [{"tool": t, "arguments": parsed.get("arguments", {})}]

            valid_actions = []
            for act in actions_list:
                if isinstance(act, dict):
                    t_name = str(act.get("tool", "")).strip()
                    if tool_registry.is_registered(t_name):
                        # Filter invalid open_application args
                        if t_name == "open_application":
                            app_arg = str(act.get("arguments", {}).get("application", "")).lower().strip()
                            if not any(valid_app in app_arg for valid_app in self.VALID_APP_NAMES):
                                logger.warning(f"Rejecting invalid application name '{app_arg}' for open_application")
                                continue
                        valid_actions.append({
                            "tool": t_name,
                            "arguments": act.get("arguments", {}) if isinstance(act.get("arguments"), dict) else {}
                        })

            first_tool = valid_actions[0]["tool"] if valid_actions else None
            first_args = valid_actions[0]["arguments"] if valid_actions else {}

            return {
                "intent": intent_type if valid_actions or intent_type in ("CONVERSATION", "SYSTEM_INFORMATION") else "CONVERSATION",
                "actions": valid_actions,
                "tool": first_tool,
                "arguments": first_args,
                "response": resp_val if resp_val else ("Done." if valid_actions else "I'm listening, Sriram. How can I help?")
            }

        clean_text = raw_output.strip().strip('"').strip("`")
        if not clean_text or clean_text.startswith("{") or "tool" in clean_text.lower():
            clean_text = "I'm here, Sriram. How can I assist you?"

        return {
            "intent": "CONVERSATION",
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

    def _rule_based_check(self, user_input: str) -> Optional[Dict[str, Any]]:
        norm_inp = re.sub(r'[^\w\s]', '', user_input.lower()).strip()

        # System local time and date checks
        if norm_inp in ("what time is it", "what is the current time", "tell me the time", "what time is it now", "current time", "what time is it right now"):
            now_str = datetime.datetime.now().strftime("%I:%M %p").lstrip("0")
            return {
                "intent": "SYSTEM_INFORMATION",
                "actions": [],
                "tool": None,
                "arguments": {},
                "response": f"It's {now_str}."
            }

        if norm_inp in ("what date is it", "what is the date today", "what date is today", "what day is today", "tell me the date", "today date"):
            date_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return {
                "intent": "SYSTEM_INFORMATION",
                "actions": [],
                "tool": None,
                "arguments": {},
                "response": f"Today is {date_str}."
            }

        # Fix "Open the first document" bug: Relative UI object requests -> Dedicated screen interaction tool
        if any(p in norm_inp for p in ("first document on the screen", "open the first document", "open first document", "first file on the screen", "open the first file", "click the first file")):
            return {
                "intent": "SCREEN_INTERACTION",
                "actions": [{"tool": "open_screen_item", "arguments": {"description": "first document visible on the screen"}}],
                "tool": "open_screen_item",
                "arguments": {"description": "first document visible on the screen"},
                "response": "I'm opening the first document visible on your screen."
            }

        # Explicit computer shutdown check
        if any(p in norm_inp for p in ("shut down my computer", "shutdown windows", "shutdown computer", "shut down windows", "shutdown my computer", "shutdown the laptop", "shut down the laptop")):
            return {
                "intent": "DANGEROUS_SYSTEM_ACTION",
                "actions": [{"tool": "shutdown_computer", "arguments": {}}],
                "tool": "shutdown_computer",
                "arguments": {},
                "response": "You asked me to shut down the laptop. Should I continue?"
            }

        # Volume controls
        if any(p in norm_inp for p in ("increase volume", "volume up", "louder", "turn up volume", "turn up the volume", "raise volume", "turn volume up", "increase the volume")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "system_volume_up", "arguments": {}}], "tool": "system_volume_up", "arguments": {}, "response": "Done."}
        if any(p in norm_inp for p in ("decrease volume", "volume down", "quieter", "lower volume", "turn down volume", "turn down the volume", "turn volume down", "decrease the volume")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "system_volume_down", "arguments": {}}], "tool": "system_volume_down", "arguments": {}, "response": "Done."}
        if any(p in norm_inp for p in ("mute volume", "mute the volume", "mute audio", "mute sound", "mute", "unmute")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "system_mute", "arguments": {}}], "tool": "system_mute", "arguments": {}, "response": "Done."}

        # Brightness controls
        if any(p in norm_inp for p in ("increase brightness", "brightness up", "brighter", "screen brighter", "turn screen brightness up", "increase the brightness")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "system_brightness_up", "arguments": {}}], "tool": "system_brightness_up", "arguments": {}, "response": "Done."}
        if any(p in norm_inp for p in ("decrease brightness", "brightness down", "dimmer", "screen dimmer", "turn screen brightness down", "decrease the brightness")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "system_brightness_down", "arguments": {}}], "tool": "system_brightness_down", "arguments": {}, "response": "Done."}

        # Microphone & Camera Controls
        if any(p in norm_inp for p in ("mute the microphone", "mute mic", "turn off the microphone", "turn off mic", "disable microphone", "turn the microphone off", "turn mic off")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "mute_microphone", "arguments": {}}], "tool": "mute_microphone", "arguments": {}, "response": "You asked me to mute the microphone. Should I proceed?"}
        if any(p in norm_inp for p in ("turn the microphone on", "unmute mic", "unmute microphone", "turn on mic", "turn on the microphone", "turn mic on")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "unmute_microphone", "arguments": {}}], "tool": "unmute_microphone", "arguments": {}, "response": "Done. Unmuted microphone."}
        if any(p in norm_inp for p in ("turn the camera off", "turn camera off", "disable camera", "close camera", "turn camera off")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "turn_camera_off", "arguments": {}}], "tool": "turn_camera_off", "arguments": {}, "response": "You asked me to disable the camera. Should I proceed?"}
        if any(p in norm_inp for p in ("turn the camera on", "turn camera on", "open camera", "enable camera", "turn camera on")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "turn_camera_on", "arguments": {}}], "tool": "turn_camera_on", "arguments": {}, "response": "Done. Turned camera on."}
        if any(p in norm_inp for p in ("turn on the backlight", "turn on backlight", "enable backlight", "keyboard backlight")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "toggle_backlight", "arguments": {"state": "on"}}], "tool": "toggle_backlight", "arguments": {"state": "on"}, "response": "Done. Toggled keyboard backlight."}

        # Lock PC
        if any(p in norm_inp for p in ("lock my pc", "lock laptop", "lock computer", "lock pc")):
            return {"intent": "SYSTEM_CONTROL", "actions": [{"tool": "lock_pc", "arguments": {}}], "tool": "lock_pc", "arguments": {}, "response": "Done. Windows PC locked."}

        # Session Stop / Deactivation intents
        deactivation_phrases = {
            "stop", "go offline", "stop listening", "thats enough", "that's enough",
            "sleep", "deactivate", "shutdown", "turn yourself off", "turn off", "exit session"
        }
        if norm_inp in deactivation_phrases:
            return {
                "intent": "SYSTEM_CONTROL",
                "actions": [{"tool": "deactivate_session", "arguments": {}}],
                "tool": "deactivate_session",
                "arguments": {},
                "response": "Going offline."
            }

        # Session Extension intents
        extension_phrases = {
            "yes continue", "continue", "keep listening", "stay active", "stay online",
            "extend session", "keep going", "dont stop", "don't stop",
            "stay with me", "yes", "yeah", "sure", "keep it online", "keep me active"
        }
        if norm_inp in extension_phrases:
            return {
                "intent": "SYSTEM_CONTROL",
                "actions": [{"tool": "extend_session", "arguments": {}}],
                "tool": "extend_session",
                "arguments": {},
                "response": "Sure, I'll stay online."
            }

        # Conversational / Knowledge questions (MUST NOT OPEN BROWSER / CHROME)
        if norm_inp in ("who are you", "what is your name", "who created you", "what is your aim", "what is your aim in life", "what is your purpose", "what can you do", "tell me something interesting", "thank you", "thanks", "are you there"):
            if norm_inp in ("who are you", "what is your name"):
                resp = "I'm HP, your personal AI assistant. I can help you control your laptop, manage tasks, answer questions, and interact with your applications."
            elif norm_inp in ("what is your aim", "what is your aim in life", "what is your purpose"):
                resp = "My aim is to help you seamlessly control your Windows laptop, manage browser tasks, answer questions, and assist with your engineering projects."
            elif norm_inp in ("thank you", "thanks"):
                resp = "You're welcome, Sriram!"
            elif norm_inp == "are you there":
                resp = "Yes, Sriram! I'm here and ready."
            else:
                resp = "I'm HP, your personal AI assistant. I can help you control your laptop, manage Chrome tabs, monitor hardware, and answer your questions."

            return {
                "intent": "CONVERSATION",
                "actions": [],
                "tool": None,
                "arguments": {},
                "response": resp
            }

        if norm_inp in ("who is sriram", "tell me about sriram", "who is your owner", "who do you belong to"):
            return {
                "intent": "CONVERSATION",
                "actions": [],
                "tool": None,
                "arguments": {},
                "response": "My owner is Sriram, an ambitious engineering student passionate about AI, software development, machine learning, deep learning, computer vision, Java, Python, Spring Boot, FastAPI, React, AI agents, and hackathons."
            }

        if norm_inp in ("tell me a joke", "make me laugh"):
            return {
                "intent": "CONVERSATION",
                "actions": [],
                "tool": None,
                "arguments": {},
                "response": "Why do programmers prefer dark mode? Because light attracts bugs!"
            }

        if norm_inp in ("good morning", "good morning hp", "hello hp", "hi hp", "hey hp", "how are you"):
            if norm_inp == "how are you":
                resp = "I'm doing great, Sriram! Ready to assist you."
            else:
                resp = "Hello Sriram! How can I assist you today?"
            return {
                "intent": "CONVERSATION",
                "actions": [],
                "tool": None,
                "arguments": {},
                "response": resp
            }

        if "explain polymorphism" in norm_inp or "what is polymorphism" in norm_inp or norm_inp == "what is java":
            if "polymorphism" in norm_inp:
                resp = "Polymorphism in object-oriented programming allows objects of different classes to be treated as objects of a common superclass, enabling method overriding and dynamic method dispatch."
            else:
                resp = "Java is a popular class-based, object-oriented programming language designed to have as few implementation dependencies as possible."
            return {
                "intent": "CONVERSATION",
                "actions": [],
                "tool": None,
                "arguments": {},
                "response": resp
            }

        inp = user_input.lower().strip()
        separators = [", then ", " then ", " after that ", " and then ", " next then "]
        clauses = []
        for sep in separators:
            if sep in inp:
                clauses = [c.strip() for c in inp.split(sep) if c.strip()]
                break

        if not clauses:
            clauses = [inp]

        actions = []
        for clause in clauses:
            single = self._single_clause_check(clause)
            if single and single.get("actions"):
                actions.extend(single["actions"])

        if actions:
            resp = "Done." if len(actions) == 1 else f"Sure! Performing {len(actions)} steps for you."
            return {
                "intent": "COMPUTER_CONTROL" if "browser_" not in actions[0]["tool"] else "BROWSER_CONTROL",
                "actions": actions,
                "tool": actions[0]["tool"],
                "arguments": actions[0]["arguments"],
                "response": resp
            }

        return None

    def _single_clause_check(self, inp: str) -> Optional[Dict[str, Any]]:
        # Tab & Browser interaction checks
        if any(p in inp for p in ("new tab", "open a new tab", "open new tab", "create a new tab", "create another tab", "give me a new browser tab", "open one more tab", "start a new tab")):
            return {"actions": [{"tool": "browser_new_tab", "arguments": {}}]}
        if any(p in inp for p in ("close the tab", "close tab", "close current tab", "close this tab", "get rid of this tab", "close this browser tab")):
            return {"actions": [{"tool": "browser_close_tab", "arguments": {}}]}
        if any(p in inp for p in ("next tab", "switch tab", "switch tabs", "switch to next tab", "switch to the next tab", "go to next tab", "move to next tab")):
            return {"actions": [{"tool": "browser_next_tab", "arguments": {}}]}
        if any(p in inp for p in ("previous tab", "prior tab", "go to previous tab", "switch to previous tab")):
            return {"actions": [{"tool": "browser_previous_tab", "arguments": {}}]}
        if any(p in inp for p in ("go back", "browser back", "navigate back", "go to the previous page")):
            return {"actions": [{"tool": "browser_back", "arguments": {}}]}
        if any(p in inp for p in ("go forward", "browser forward", "navigate forward", "go to the next page")):
            return {"actions": [{"tool": "browser_forward", "arguments": {}}]}
        if any(p in inp for p in ("refresh the page", "refresh", "reload page", "refresh page")):
            return {"actions": [{"tool": "browser_refresh", "arguments": {}}]}
        if any(p in inp for p in ("scroll down", "page down")):
            return {"actions": [{"tool": "scroll_down", "arguments": {}}]}
        if any(p in inp for p in ("scroll up", "page up")):
            return {"actions": [{"tool": "scroll_up", "arguments": {}}]}

        # Folder search & opening
        if (" folder" in inp or " directory" in inp) and (inp.startswith("open ") or inp.startswith("find ") or inp.startswith("show ") or inp.startswith("launch ")):
            folder_query = inp
            for prefix in ("open ", "find ", "show me ", "show ", "launch "):
                if folder_query.startswith(prefix):
                    folder_query = folder_query[len(prefix):].strip()
                    break
            return {"actions": [{"tool": "find_and_open_folder", "arguments": {"name": folder_query}}]}

        # Open application
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
                
                # Check if app_name matches valid app names
                if any(valid_app in app_name for valid_app in self.VALID_APP_NAMES):
                    return {"actions": [{"tool": "open_application", "arguments": {"application": app_name}}]}

        # System info tools
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

        # Web & YouTube Search
        if inp.startswith("search youtube for ") or inp.startswith("search youtube "):
            q = inp.replace("search youtube for ", "").replace("search youtube ", "").strip()
            return {"actions": [{"tool": "search_youtube", "arguments": {"query": q}}]}
        if inp.startswith("search google for ") or inp.startswith("search web for ") or inp.startswith("search for "):
            q = inp.replace("search google for ", "").replace("search web for ", "").replace("search for ", "").strip()
            return {"actions": [{"tool": "search_web", "arguments": {"query": q}}]}

        if inp in ("take screenshot", "capture screen", "take a screenshot"):
            return {"actions": [{"tool": "take_screenshot", "arguments": {}}]}
        if inp in ("read clipboard", "get clipboard"):
            return {"actions": [{"tool": "read_clipboard", "arguments": {}}]}

        if inp in ("prepare my laptop for coding", "coding mode"):
            return {"actions": [{"tool": "run_preset_workflow", "arguments": {"workflow_name": "coding"}}]}
        if inp in ("dsa study session", "start dsa", "start a 90 minute dsa study session"):
            return {"actions": [{"tool": "run_preset_workflow", "arguments": {"workflow_name": "dsa_study"}}]}

        return None
