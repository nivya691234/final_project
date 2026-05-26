# Remediation & Actions Guide

## Where Remediation Actually Happens

### 1. **Automatic Remediation (No User Input Required)**

#### Location: `core/action_policy.py` → `core/remediation.py`

**Flow:**
```
System Analysis
    ↓
Root Cause Detection
    ↓
Prediction Engine
    ↓
ActionPolicyEngine.run()
    ├─ _from_root_cause()          [severity ≥ MIN_SEVERITY]
    ├─ _from_failure_probability() [probability ≥ THRESHOLD]
    └─ _from_recommendations()     [confidence → action map]
    ↓
_enqueue_or_execute()
    └─ if AUTO_POLICY_MODE == "auto": RemediationEngine.execute_action()
    ↓
Log: "Remediation executing: {action} on target={process} pid={pid}"
```

**When it runs:**
- Every 5 seconds (ANALYSIS_EVERY_N)
- Triggered by dashboard_server analysis cycle
- Automatically applies if `AUTO_POLICY_MODE = "auto"` in config

**What it does:**
- Reads latest root cause from database
- Checks severity against `AUTO_SEVERITY_MIN`
- Maps cause to action preferences
- Executes action via `RemediationEngine`
- Logs result to database (`action_queue` table)

---

### 2. **AI Chatbot Interface (Requires User Confirmation)**

#### Location: `core/llm_agent.py`

**Current Behavior (Fallback Mode - No API Key):**
```
User Message
    ↓
LlmAgent.process_message()
    ↓
_fallback_keyword_matcher()
    ├─ Parses: "kill", "restart", "suspend", "limit cpu", etc.
    ├─ Looks for: target process name or PID
    ├─ If found: suggests action
    └─ If not found: asks for more info
    ↓
Response: either action suggestion or request for clarification
```

**Why it asks for PID:**
```python
# In llm_agent.py, fallback mode:
pid = self._parse_pid(msg)  # Looks for "pid XXXX" in user message
if not pid:
    # Falls back to asking
```

**Examples from logs:**
```
User: "Set maximum thread limits in the 'OfficeClickToRun.exe'"
AI:   "I cannot set maximum thread limits for 'OfficeClickToRun.exe' 
       as this functionality is not available."
       
↳ Reason: "set maximum thread limits" is not in REC_ACTION_MAP
↳ Missing: keyword mapping for thread limit configuration
```

---

### 3. **Remediation Engine (The Actual Executor)**

#### Location: `core/remediation.py`

**Available Actions:**

| Action | What It Does | Usage |
|--------|-------------|-------|
| **kill** | Terminate process immediately | `RemediationEngine.execute_action("kill", target="explorer.exe")` |
| **restart** | Kill + relaunch (requires PID) | `execute_action("restart", target="svc", pid=1234)` |
| **suspend** | Pause process (not kill) | `execute_action("suspend", pid=1234)` |
| **resume** | Continue a suspended process | `execute_action("resume", pid=1234)` |
| **limit_cpu** | Restrict to core 0 only | `execute_action("limit_cpu", target="chrome.exe")` |
| **set_affinity** | Pin to specific cores | `execute_action("set_affinity", pid=1234, cores=[0,1,2])` |
| **lower_priority** | Reduce scheduling priority | `execute_action("lower_priority", pid=1234)` |
| **disable_startup** | Remove from Windows Startup | `execute_action("disable_startup", target="sketchy.exe")` |

**Code Path:**
```python
RemediationEngine.execute_action()
    ↓
_get_processes(target or pid)  # Find matching process(es)
    ↓
for each process:
    ├─ Apply action (kill/suspend/etc)
    ├─ Catch errors (AccessDenied, NoSuchProcess)
    └─ Track success/failure
    ↓
Return: {"success": bool, "message": str}
```

---

## Configuration: When Actions Are Applied

### File: `config/settings.py`

```python
# ── Auto-remediation policy (rule-based, no AI required) ─────────────────
AUTO_POLICY_ENABLED = True              # Master switch — turn OFF to disable
AUTO_POLICY_MODE = "auto"               # "auto" = execute, "prompt" = ask
AUTO_SEVERITY_MIN = "LOW"               # Only act on this severity or higher
AUTO_PROB_THRESHOLD = 0.75              # Failure probability threshold (0-1)
AUTO_ALLOWED_ACTIONS = [
    "limit_cpu",
    "set_affinity",
    "lower_priority",
    "suspend",
    "resume",
    "kill",
    # "restart",  # Manual only
]
AUTO_DEDUP_WINDOW_SEC = 600             # Don't repeat same action for 10 min
AUTO_MAX_PROPOSALS = 3                  # Max 3 actions per cycle
```

### Automatic Action Mappings

**From Root Causes:**
```python
CAUSE_ACTION_PREFS = {
    "Memory Leak":         ["restart", "kill", "lower_priority"],
    "CPU Runaway":         ["limit_cpu", "lower_priority", "restart", "kill"],
    "Thread Leak":         ["restart", "kill"],
    "Resource Exhaustion": ["restart", "kill"],
}
```

**From Recommendations:**
```python
REC_ACTION_MAP = [
    ("restart", "restart"),
    ("kill", "kill"),
    ("lower priority", "lower_priority"),
    ("limit", "limit_cpu"),
]
```

---

## Action History & Filters

### Where Actions Are Stored

**Database Table:** `action_queue`

**Columns:**
```
id, proposal_id, action, target, pid, status, reason, severity, 
source (root_cause|prediction|recommendation), 
created_at, executed_at
```

### Query Actions via Dashboard API

**Endpoint:** `GET /api/pending-actions`

**Response:**
```json
{
  "actions": [
    {
      "id": 123,
      "action": "limit_cpu",
      "target": "TextInputHost.exe",
      "pid": 11284,
      "status": "EXECUTED",
      "severity": "HIGH",
      "reason": "CPU Runaway (HIGH)",
      "source": "root_cause",
      "created_at": 1716201000,
      "executed_at": 1716201005
    }
  ]
}
```

### Filter By Status

**In core/action_policy.py:**
```python
# Status values:
# - "QUEUED"   → Waiting for execution (prompt mode)
# - "EXECUTED" → Successfully applied
# - "FAILED"   → Error during execution
```

### View All Recent Actions

**CLI/Python:**
```python
from database.db_manager import DatabaseManager
db = DatabaseManager()

# Get all executed actions (last 100)
actions = db.get_action_history(limit=100)
for action in actions:
    print(f"{action['status']}: {action['action']} on {action['target']} ({action['reason']})")

# Get by status
auto_killed = db._query(
    "SELECT * FROM action_queue WHERE action='kill' AND status='EXECUTED' LIMIT 20"
)
```

---

## Why AI Isn't Autonomous (And How to Fix It)

### Problem 1: Fallback Mode (No API Key)

**Current:**
```
User: "fix the TextInputHost issue"
AI:   (No API key detected, using fallback)
      → Keyword matcher looks for "pid XXXX"
      → Not found → asks for PID
```

**Solution:** Add API key to `config/settings.py`

```python
GEMINI_API_KEY = "your-key-here"  # OR
OPENAI_API_KEY = "your-key-here"
```

### Problem 2: LLM Agent is Designed for Chat, Not Autonomous Action

**Current Design:**
```
LlmAgent = Chat Interface (suggests actions)
ActionPolicyEngine = Autonomous Engine (applies actions)
```

**Why separate?**
- Safety: Chat lets users review first
- Flexibility: ActionPolicyEngine handles clear-cut cases automatically
- Both can be active simultaneously

### Problem 3: AI Lacking Contextual Information

**Current fallback behavior:**
```python
# In llm_agent.py line 126+
msg = user_message.lower()
pid = self._parse_pid(msg)  # Must extract from USER text

# Better approach:
pid = self.db.get_latest_pid_for(target)  # Query DB instead
```

---

## Making AI More Autonomous

### Step 1: Enable Real LLM

```python
# config/settings.py
GEMINI_API_KEY = "AIzaSyD..."  # Get from https://aistudio.google.com/app/apikeys
```

### Step 2: Enhance System State Injection

**Current:** (llm_agent.py line 60)
```python
def _get_system_state_context(self) -> str:
    rc_latest = self.db.get_latest_root_cause() or {}
    # Only 1 root cause!
```

**Better:** Inject all relevant data

```python
def _get_system_state_context(self) -> str:
    rc_latest = self.db.get_latest_root_cause() or {}
    pred = self.db.get_latest_prediction() or {}
    recs = self.db.get_recommendations(limit=3)
    top_procs = self.db.get_top_processes(limit=5)
    
    context = f"""
    ROOT CAUSE: {rc_latest.get('cause')} on {rc_latest.get('name')} (PID: {top_procs[0]['pid']})
    FAILURE PROBABILITY: {pred.get('failure_probability'):.1%}
    RECOMMENDATIONS: {[r['recommendation'] for r in recs]}
    """
    return context
```

### Step 3: Bind AI to Auto-Remediation

**Current:** AI only suggests; ActionPolicyEngine auto-executes

**Better:** Let AI feed high-confidence actions to ActionPolicyEngine

```python
# In dashboard_server.py or monitor_agent.py
user_input = "fix the aging"
response = llm_agent.process_message(user_input)

if response.get("action"):
    # High confidence → let ActionPolicyEngine execute autonomously
    if response["action"].get("confidence", 0) > 0.8:
        remediator.execute_action(
            response["action"]["type"],
            target=response["action"]["target"],
            pid=response["action"]["pid"]
        )
    else:
        # Low confidence → enqueue for manual review
        db.insert_action_item(response["action"])
```

---

## Complete Action Execution Example

### User Request
```
"Kill the TextInputHost process because it's causing CPU runaway."
```

### Automatic Flow (if detected by analyzer)
```
1. TrendAnalyzer.analyze_system()
   → Detects CPU runaway slope > threshold
   
2. RootCauseEngine.run()
   → Identifies "TextInputHost.exe" as cause
   → Stores: {name: "TextInputHost.exe", cause: "CPU Runaway", severity: "HIGH"}
   
3. ActionPolicyEngine.run()
   → Reads latest root cause
   → CAUSE_ACTION_PREFS["CPU Runaway"] = ["limit_cpu", "lower_priority", "restart", "kill"]
   → _pick_allowed_action() selects first allowed: "limit_cpu"
   
4. RemediationEngine.execute_action(
       action="limit_cpu",
       target="TextInputHost.exe",
       pid=11284
   )
   → Finds all TextInputHost.exe processes
   → Calls p.cpu_affinity([0]) on each
   → Logs: "Remediation executing: limit_cpu on target=TextInputHost.exe pid=11284"
   
5. Database log entry
   → status: "EXECUTED"
   → reason: "CPU Runaway (HIGH)"
   → source: "root_cause"
```

### Manual Flow (via Chat)
```
1. User: "limit_cpu on pid 11284"

2. LlmAgent.process_message()
   → Matches keyword "limit_cpu" + "pid 11284"
   → Returns: {"reply": "...", "action": {"type": "limit_cpu", "pid": 11284}}

3. Dashboard API calls RemediationEngine directly
   → RemediationEngine.execute_action("limit_cpu", pid=11284)
   → Same result as automatic flow
```

---

## Debugging: Why an Action Wasn't Taken

### Check 1: Is AUTO_POLICY_ENABLED?
```python
from config.settings import AUTO_POLICY_ENABLED
print(AUTO_POLICY_ENABLED)  # Must be True
```

### Check 2: Is severity ≥ AUTO_SEVERITY_MIN?
```python
# Dashboard → Root Cause → Check "severity" column
# Must be one of: CRITICAL, HIGH, MEDIUM, LOW
# And must be >= AUTO_SEVERITY_MIN (default "LOW")
```

### Check 3: Is the action in AUTO_ALLOWED_ACTIONS?
```python
from config.settings import AUTO_ALLOWED_ACTIONS
print(AUTO_ALLOWED_ACTIONS)
# If action ("restart") not in list, it will be skipped
```

### Check 4: Is the process ignored?
```python
from config.settings import IGNORE_PROCESS_NAMES
print(IGNORE_PROCESS_NAMES)  # If target is here, it's skipped
```

### Check 5: Is it in dedup window?
```python
# Same action on same target within AUTO_DEDUP_WINDOW_SEC is skipped
# Default: 600 seconds (10 minutes)
```

### Check 6: View action queue
```python
# Dashboard → Pending Actions
# OR via API: GET /api/pending-actions
# Look for your process—if not there, root cause wasn't detected
```

