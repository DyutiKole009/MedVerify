"""
Loads and parses SKILL.md definition files from .agents/skills/ for LLM Skill Agent.
"""
from pathlib import Path
from typing import Dict
from src.utils.logger import logger


def get_skills_directory() -> Path:
    """Finds the .agents/skills directory relative to project root or current working dir."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    candidates = [
        backend_dir / ".agents" / "skills",
        backend_dir.parent / ".agents" / "skills",
        Path(".agents/skills").resolve(),
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return candidates[1]


def load_skills_documentation() -> Dict[str, str]:
    """
    Loads all SKILL.md files from .agents/skills/ directory.
    Returns a dictionary mapping skill name -> full SKILL.md content.
    """
    skills_dir = get_skills_directory()
    if not skills_dir.exists():
        logger.warning(f"Skills directory not found at {skills_dir}")
        return {}

    skills_docs: Dict[str, str] = {}
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_file.parent.name
        try:
            content = skill_file.read_text(encoding="utf-8")
            skills_docs[skill_name] = content
        except Exception as exc:
            logger.warning(f"Could not read {skill_file}: {exc}")

    return skills_docs


def build_skills_system_prompt() -> str:
    """
    Builds the system prompt for the Skill Agent incorporating the exact
    instructions, procedures, and rules from all available SKILL.md files.
    """
    docs = load_skills_documentation()
    sections = [
        "You are the MedVerify Skill Agent, an autonomous clinical and regulatory medicine investigator.",
        "Your task is to select and call the appropriate skill tools to verify medicines against CDSCO records.",
        "",
        "MANDATORY OPERATIONAL RULES:",
        "1. YOU must dynamically select and invoke the appropriate tool(s) based on the user's input.",
        "2. When a batch number is given, call `check_batch(batch_no=...)` to query official regulatory records.",
        "3. When a drug name or fuzzy text is provided, call `search_drug(fuzzy_text=...)` to resolve OCR typos or misspellings.",
        "4. Call `get_community_reports(batch_no=..., drug_name=...)` to check crowd-sourced safety signals.",
        "5. Call `get_manufacturer_history(manufacturer_name=...)` to assess the manufacturer's regulatory track record.",
        "6. If source citations or regulatory text are requested, call `get_notice(source_document_s3_key=...)`.",
        "7. NEVER claim a medicine is genuine or safe. Always reinforce that absence of a flag is not proof of safety.",
        "8. Conclude with a clear, concise consumer summary explaining what official and community evidence exists.",
        "",
        "DETAILED SKILL GUIDELINES & SPECIFICATIONS (from SKILL.md):",
    ]

    for name, content in docs.items():
        sections.append(f"\n==================== SKILL: {name} ====================\n{content}\n")

    return "\n".join(sections)
