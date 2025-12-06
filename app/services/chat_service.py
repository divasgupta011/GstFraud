# app/services/chat_service.py

from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from langchain_core.messages import SystemMessage, HumanMessage

from ..genai.client import get_llm
from ..services.risk_service import (
    compute_vendor_risk,
    compute_all_vendors_risk,
)
from ..neo4j_client import get_neo4j_driver


def _plan_action(query: str) -> Dict[str, Any]:
    """
    Use LLM (Groq) to decide which internal action to call.
    Returns a dict like:
    {
      "action": "GET_VENDOR_RISK",
      "params": {"vendor_id": 1}
    }
    """
    llm = get_llm()
    if llm is None:
        # fallback: no planning if LLM disabled
        return {"action": "GENERAL", "params": {}}

    system_prompt = (
        "You are a planner for a GST fraud risk assistant. "
        "Your job is ONLY to choose which action the backend should take "
        "based on the user query, and return a strict JSON object.\n\n"
        "Supported actions:\n"
        "1) GET_VENDOR_RISK: when user asks about risk of a specific vendor.\n"
        "   params: {\"vendor_id\": <int>}\n\n"
        "2) LIST_HIGH_RISK_VENDORS: when user asks for top risky vendors.\n"
        "   params: {\"limit\": <int>} (default 5)\n\n"
        "3) LIST_CYCLES: when user asks about circular trading / loops.\n"
        "   params: {\"max_length\": <int>} (default 5)\n\n"
        "4) GENERAL: when question is general explanation or small talk.\n"
        "   params: {}.\n\n"
        "Return ONLY JSON, no extra text."
    )

    user_prompt = f'User query: "{query}"\n\nDecide action and params.'

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    text = response.content

    # Try to parse JSON manually (LLM should return JSON only)
    import json

    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Planner output not a dict")
        action = data.get("action", "GENERAL")
        params = data.get("params", {}) or {}
        return {"action": action, "params": params}
    except Exception:
        # fallback
        return {"action": "GENERAL", "params": {}}


def _run_list_cycles(max_length: int = 5) -> Dict[str, Any]:
    """
    Run a simple cycles query in Neo4j (similar logic to /graph/cycles).
    """
    if max_length < 2:
        max_length = 2
    if max_length > 10:
        max_length = 10

    driver = get_neo4j_driver()

    query = f"""
    MATCH p = (v:Vendor)-[:SUPPLIES_TO*2..{max_length}]->(v)
    RETURN [n IN nodes(p) | {{id: n.id, name: n.name, gstin: n.gstin}}] AS vendors
    """

    unique_cycles: Dict[str, Any] = {}
    from typing import Tuple, List as TList

    def canonical_key(ids: TList[int]) -> Tuple[int, ...]:
        if not ids:
            return tuple()
        ids = list(ids)
        n = len(ids)
        rotations = []
        for i in range(n):
            rot = ids[i:] + ids[:i]
            rotations.append(rot)
        rev = list(reversed(ids))
        for i in range(n):
            rot_rev = rev[i:] + rev[:i]
            rotations.append(rot_rev)
        return min(tuple(r) for r in rotations)

    with driver.session() as session:
        result = session.run(query)
        for record in result:
            vendors_in_path = record["vendors"]
            if not vendors_in_path or len(vendors_in_path) < 3:
                continue
            ids = [v["id"] for v in vendors_in_path]
            if ids[0] == ids[-1]:
                ids = ids[:-1]
            if len(ids) < 2:
                continue
            key = canonical_key(ids)
            if key not in unique_cycles:
                unique_cycles[key] = {
                    "length": len(ids),
                    "vendors": vendors_in_path,
                }

    cycles_list = list(unique_cycles.values())
    return {
        "count": len(cycles_list),
        "max_length_used": max_length,
        "cycles": cycles_list,
    }


def handle_chat(query: str, db: Session) -> Dict[str, Any]:
    """
    Main chat orchestrator:
    1) Use LLM to plan which tool/action to use
    2) Execute that tool using our backend logic
    3) Use LLM again to generate a natural language answer
    """
    llm = get_llm()
    if llm is None:
        # No LLM configured → just return fallback
        return {
            "answer": "LLM is not configured. Please set GROQ_API_KEY to enable chat.",
            "tool_call": None,
            "raw_tool_result": None,
        }

    plan = _plan_action(query)
    action = plan["action"]
    params = plan["params"]

    tool_result: Optional[Dict[str, Any]] = None

    # --- Execute tools based on action ---

    if action == "GET_VENDOR_RISK":
        vendor_id = int(params.get("vendor_id", 0) or 0)
        if vendor_id <= 0:
            # invalid vendor_id, fallback
            action = "GENERAL"
        else:
            try:
                risk = compute_vendor_risk(db, vendor_id)
                tool_result = {"type": "vendor_risk", "data": risk}
            except ValueError:
                tool_result = {
                    "type": "error",
                    "message": f"Vendor {vendor_id} not found.",
                }

    if action == "LIST_HIGH_RISK_VENDORS":
        limit = int(params.get("limit", 5) or 5)
        if limit <= 0 or limit > 50:
            limit = 5
        all_risks = compute_all_vendors_risk(db)
        tool_result = {
            "type": "risk_list",
            "data": all_risks[:limit],
        }

    if action == "LIST_CYCLES":
        max_length = int(params.get("max_length", 5) or 5)
        cycles = _run_list_cycles(max_length=max_length)
        tool_result = {
            "type": "cycles",
            "data": cycles,
        }

    # --- Now let LLM generate final answer ---

    system_prompt = (
        "You are a GST fraud and vendor risk assistant. "
        "You receive the user's query and some structured tool results from a backend. "
        "Your job is to explain clearly, in a few paragraphs or bullet points, "
        "without exposing internal JSON structure. If tool_result.type == 'error', "
        "politely explain the issue."
    )

    if tool_result is None or action == "GENERAL":
        # No tool used or fallback → general explanation only
        user_prompt = f"""
User query:
{query}

Tool result:
None

Answer the user's question to the best of your ability as a GST risk assistant.
If the question is not about GST/fraud, answer briefly or say you focus on GST vendor risk.
"""
    else:
        user_prompt = f"""
User query:
{query}

Planned action: {action}

Tool result (structured JSON):
{tool_result}

Task:
Explain this to the user in clear language. If it is a list of risky vendors, summarize the top ones.
If it's a single vendor risk, explain why the vendor is high/medium/low risk.
If it's about circular trading cycles, describe the loops and involved vendors.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    answer_text = response.content

    return {
        "answer": answer_text,
        "tool_call": {
            "action": action,
            "params": params,
        },
        "raw_tool_result": tool_result,
    }
