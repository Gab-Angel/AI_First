import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def get_prompt(prompt_name: str) -> str:
    """
    Carrega um prompt Jinja2 (.j2) e injeta automaticamente
    as regras de negócio definidas em business_rules.json.
    """

    base_dir = Path(__file__).resolve().parent

    prompt_path = base_dir / f"{prompt_name}.j2"
    rules_path = base_dir / "business_rules.json"

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt '{prompt_name}.j2' não encontrado em {base_dir}"
        )

    if not rules_path.exists():
        raise FileNotFoundError(
            f"'business_rules.json' não encontrado em {base_dir}"
        )

    # carrega regras de negócio
    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    # ambiente Jinja2
    env = Environment(
        loader=FileSystemLoader(base_dir),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template(f"{prompt_name}.j2")

    return template.render(**rules)


