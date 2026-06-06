from datetime import datetime

ROLE_COLORS = {
    "user": "#58a6ff",
    "llm_response": "#3fb950",
    "evaluator_judgment": "#d29922",
    "harness_followup": "#bc8cff",
    "final_output": "#3fb950",
}

ROLE_LABELS = {
    "user": "User Query",
    "llm_response": "LLM Response",
    "evaluator_judgment": "Evaluator Judgment",
    "harness_followup": "Harness Follow-Up",
    "final_output": "Final Output",
}

VALID_ROLES = {"user", "llm_response", "evaluator_judgment", "harness_followup", "final_output"}


class InteractionChain:
    def __init__(self, user_query: str):
        if not user_query or not user_query.strip():
            raise ValueError("user_query must not be empty")
        self.user_query = user_query
        self.steps: list[dict] = []
        self.total_iterations: int = 0
        self.early_stopped: bool = False
        self.final_output: str = ""
        self.referenced_files: list[str] = []
        self.session_id: str = ""

    def add_step(self, role: str, content: str, iteration: int):
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Must be one of {sorted(VALID_ROLES)}")
        self.steps.append({
            "role": role,
            "content": content,
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
        })

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_query": self.user_query,
            "steps": self.steps,
            "total_iterations": self.total_iterations,
            "early_stopped": self.early_stopped,
            "final_output": self.final_output,
            "referenced_files": self.referenced_files,
        }

    def to_markdown(self) -> str:
        return _dict_to_markdown(self.to_dict())


def _dict_to_markdown(chain_dict: dict) -> str:
    lines = [
        "# Audit Harness — Interaction Chain",
        "",
        f"**User Query:** {chain_dict.get('user_query', '')}",
        f"**Total Iterations:** {chain_dict.get('total_iterations', 0)}",
        f"**Early Stopped:** {'Yes' if chain_dict.get('early_stopped') else 'No'}",
        "",
        "---",
        "",
    ]
    referenced = chain_dict.get("referenced_files", [])
    if referenced:
        lines.append("## Referenced Files")
        lines.append("")
        for f in referenced:
            lines.append(f"- `{f}`")
        lines.append("")

    for i, step in enumerate(chain_dict.get("steps", [])):
        role = step.get("role", "unknown")
        color = ROLE_COLORS.get(role, "#ffffff")
        label = ROLE_LABELS.get(role, role)
        lines.append(f"## Step {i+1}: <span style=\"color:{color}\">{label}</span> (Iteration {step.get('iteration', '?')})")
        lines.append("")
        lines.append(f"*Timestamp: {step.get('timestamp', '')}*")
        lines.append("")
        lines.append(step.get("content", ""))
        lines.append("")
        lines.append("---")
        lines.append("")

    if chain_dict.get("final_output"):
        lines.append("## Final Audit Output")
        lines.append("")
        lines.append(chain_dict["final_output"])

    return "\n".join(lines)
