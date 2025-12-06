# app/genai/risk_explainer.py

from typing import Dict, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from .client import get_llm


def generate_risk_explanation(risk_data: Dict[str, Any]) -> Optional[str]:
    """
    Given the risk JSON (from compute_vendor_risk), call Groq LLM (via LangChain)
    to produce a short, human-readable explanation.
    Returns None if LLM is not configured.
    """
    llm = get_llm()
    if llm is None:
        return None

    vendor = risk_data["vendor"]
    score = risk_data["risk_score"]
    level = risk_data["risk_level"]
    flags = risk_data["flags"]
    details = risk_data["details"]

    system_prompt = (
        "You are an assistant that explains GST vendor fraud risk "
        "to compliance and finance teams in concise, clear language."
    )

    user_prompt = f"""
Vendor:
- Name: {vendor['name']}
- GSTIN: {vendor['gstin']}
- State: {vendor.get('state')}
- Address: {vendor.get('address')}
- PAN: {vendor.get('pan')}

Risk:
- Risk score: {score}
- Risk level: {level}
- Flags: {', '.join(flags) if flags else 'None'}

Details (raw JSON):
{details}

Task:
Explain in 3–5 bullet points why this vendor has this risk score.
Be specific and reference patterns like circular trading, shared addresses,
no invoices, etc. Avoid repeating raw JSON; summarize it in plain English.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # LangChain style: invoke() returns an AIMessage
    response = llm.invoke(messages)
    explanation = response.content
    return explanation
