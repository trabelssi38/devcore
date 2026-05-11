class BaseAdapter:
    engine_name = "base"

    def build_prompt(self, handoff: dict) -> str:
        constraints = "\n".join(f"- {item}" for item in handoff["constraints"])
        return "\n".join(
            [
                f"# Engine: {self.engine_name}",
                "",
                f"Intent: {handoff['intent']}",
                f"Context: {handoff['context_summary']}",
                "",
                "Constraints:",
                constraints,
                "",
                f"Expected output: {handoff['expected_output']}",
            ]
        )

    def prepare(self, session_dir, handoff: dict) -> dict:
        prompt_path = session_dir / f"{self.engine_name}-prompt.md"
        prompt_path.write_text(self.build_prompt(handoff), encoding="utf-8")
        return {
            "engine": self.engine_name,
            "prompt_path": str(prompt_path),
            "launch_hint": f"Open {prompt_path} in {self.engine_name}",
        }
