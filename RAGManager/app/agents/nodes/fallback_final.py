"""Nodo 8: Fallback Final - Final validation for risky/sensitive content."""

from app.agents.state import AgentState


def fallback_final(state: AgentState) -> AgentState:
    """
    Fallback Final node - Validates response for risky/sensitive content.

    This node:
    1. Analyzes the generated response for risky/sensitive content
    2. Sets is_risky flag
    3. Sets error_message if risky content is detected
    4. If valid, calls Final LLM to generate final response

    Args:
        state: Agent state containing generated_response

    Returns:
        Updated state with is_risky, error_message, and final_response set
    """
    # TODO: Implement risky content detection and final LLM call
    # This should:
    # 1. Check generated_response for sensitive/risky content
    # 2. Set is_risky = True if risky content is detected
    # 3. Set error_message with appropriate message if risky
    # 4. If not risky, call Final LLM with generated_response
    # 5. Store Final LLM response in final_response

    # Placeholder: For now, we'll assume all responses are safe
    updated_state = state.copy()
    updated_state["is_risky"] = False
    updated_state["error_message"] = None

    # TODO: Call Final LLM here if not risky
    # if not updated_state["is_risky"]:
    #     updated_state["final_response"] = call_final_llm(updated_state["generated_response"])
    updated_state["final_response"] = updated_state.get("generated_response")

    return updated_state
