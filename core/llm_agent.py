"""
core/llm_agent.py
-----------------
Agentic wrapper connecting the local Software Aging Analyzer to a true Large Language Model (LLM).
Uses native urllib to send REST requests to Gemini or OpenAI, interpreting user goals intelligently.
"""

import json
import logging
import re
import urllib.request
from urllib.error import URLError, HTTPError
from config.settings import GEMINI_API_KEY, OPENAI_API_KEY
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class LlmAgent:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def process_message(self, user_msg: str) -> dict:
        """
        Takes raw user input, injects the system state context, and routes to an LLM.
        Returns a dictionary with 'reply' and optionally an 'action' object.
        """
        state_context = self._get_system_state_context()
        
        system_prompt = (
            "You are the 'Remediation AI' integrated into a server dashboard. Your goal is to help the user manage server aging and rogue processes.\n"
            f"CURRENT SYSTEM STATE:\n{state_context}\n\n"
            "ACTIONS YOU CAN TAKE:\n"
            "- 'kill': Terminate a known problematic process.\n"
            "- 'restart': Kill then relaunch the same process (PID required).\n"
            "- 'suspend': Pause a running process.\n"
            "- 'resume': Continue a paused process.\n"
            "- 'limit_cpu': Restrict a process to 1 CPU core to stop CPU runaways.\n"
            "- 'set_affinity': Assign a process to specific CPU cores (provide cores array).\n"
            "- 'lower_priority': Deprioritize a process so the OS remains responsive.\n"
            "- 'disable_startup': Disable a Startup entry by name (Windows Startup folder only).\n"
            "- 'none': If no action is needed, or the user is just chatting.\n\n"
            "INSTRUCTIONS:\n"
            "Analyze the user's message against the active system state. If they ask you to fix an issue, use your logic to select the best action for the specific process causing it.\n"
            "Respond strictly in valid JSON format without markdown blocks. Schema:\n"
            '{\n  "reply": "Conversational response explaining what you are doing. Be concise.",\n  "action": {"type": "kill|restart|suspend|resume|limit_cpu|set_affinity|lower_priority|disable_startup", "target": "process_name", "pid": 1234, "params": {"cores": [0,1]} } // Or omit action if none\n}'
        )

        try:
            if GEMINI_API_KEY:
                return self._call_gemini(system_prompt, user_msg)
            elif OPENAI_API_KEY:
                return self._call_openai(system_prompt, user_msg)
            else:
                return self._fallback_keyword_matcher(user_msg, state_context)
        except Exception as e:
            logger.error(f"LLM API Error: {e}")
            return {"reply": f"Sorry, I encountered an error connecting to the AI brain: {e}", "action": None}

    def _get_system_state_context(self) -> str:
        rc_latest = self.db.get_latest_root_cause() or {}
        pred = self.db.get_latest_prediction() or {}
        
        target = rc_latest.get("name", "system")
        cause = rc_latest.get("cause", "Normal")
        sev = rc_latest.get("severity", "LOW")
        prob = pred.get("failure_probability", 0) * 100
        
        if target == "system" or sev == "LOW":
            return f"System is currently healthy. Failure probability is {prob:.1f}%."
        return f"WARNING: {sev} severity {cause} detected. It is being caused by background process '{target}'. System failure probability is currently at {prob:.1f}%."

    def _clean_json_response(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return {"reply": text, "action": None}

    def _call_gemini(self, system: str, user: str) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.2}
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._clean_json_response(text)

    def _call_openai(self, system: str, user: str) -> dict:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.2
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        })
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            text = data["choices"][0]["message"]["content"]
            return self._clean_json_response(text)
            
    def _fallback_keyword_matcher(self, user_msg: str, state: str) -> dict:
        msg = user_msg.lower()
        reply = "To unlock true AI capabilities, please add a GEMINI_API_KEY or OPENAI_API_KEY to 'config/settings.py'. For now, I am operating in basic keyword mode.\n\n"
        
        # Simple fallback mimicking previous logic
        target = self.db.get_latest_root_cause().get("name") if self.db.get_latest_root_cause() else None
        pid = self._parse_pid(msg)
        cores = self._parse_cores(msg)

        if "disable startup" in msg:
            if target:
                return {"reply": reply + f"I can disable Startup for {target}.", "action": {"type": "disable_startup", "target": target}}

        if "restart" in msg and pid:
            return {"reply": reply + f"I can restart PID {pid}.", "action": {"type": "restart", "pid": pid, "target": target}}

        if "suspend" in msg and pid:
            return {"reply": reply + f"I can suspend PID {pid}.", "action": {"type": "suspend", "pid": pid, "target": target}}

        if "resume" in msg and pid:
            return {"reply": reply + f"I can resume PID {pid}.", "action": {"type": "resume", "pid": pid, "target": target}}

        if "affinity" in msg and pid and cores:
            return {
                "reply": reply + f"I can set CPU affinity for PID {pid} to cores {cores}.",
                "action": {"type": "set_affinity", "pid": pid, "target": target, "params": {"cores": cores}},
            }

        if "limit cpu" in msg and pid:
            return {"reply": reply + f"I can limit PID {pid} to one core.", "action": {"type": "limit_cpu", "pid": pid, "target": target}}

        if "lower priority" in msg and pid:
            return {"reply": reply + f"I can lower priority for PID {pid}.", "action": {"type": "lower_priority", "pid": pid, "target": target}}

        if ("kill" in msg or "terminate" in msg) and (pid or target):
            return {"reply": reply + f"I can kill the target now.", "action": {"type": "kill", "pid": pid, "target": target}}

        if "fix" in msg or "critical" in msg:
            if target and target != "system":
                return {"reply": reply + f"Should I kill {target} to fix the issue?", "action": {"type": "kill", "target": target}}

        available_commands = (
            "I am monitoring the system for signs of aging. If I detect an issue, I can help you with the following commands:\n"
            "- kill <process_name or pid>\n"
            "- restart <pid>\n"
            "- suspend <pid>\n"
            "- resume <pid>\n"
            "- limit cpu <pid>\n"
            "- set affinity <pid> cores <0,1>\n"
            "- lower priority <pid>\n"
            "- disable startup <process_name>\n"
            "How can I help?"
        )
        return {"reply": reply + available_commands, "action": None}

    @staticmethod
    def _parse_pid(msg: str) -> int | None:
        match = re.search(r"pid\s*(\d+)", msg)
        return int(match.group(1)) if match else None

    @staticmethod
    def _parse_cores(msg: str) -> list[int]:
        match = re.search(r"core[s]?\s*([0-9,\s]+)", msg)
        if not match:
            return []
        raw = match.group(1)
        cores = [c.strip() for c in raw.split(",") if c.strip().isdigit()]
        return [int(c) for c in cores]
