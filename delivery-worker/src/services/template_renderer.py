import logging

from jinja2 import BaseLoader, Environment

logger = logging.getLogger(__name__)

_env = Environment(loader=BaseLoader(), autoescape=True)


def render(
    subject_template: str, body_template: str, variables: dict
) -> tuple[str, str]:
    """Render subject and body Jinja2 templates with *variables*.

    Returns (subject, html_body). On render error falls back to raw template strings.
    """
    try:
        subject = _env.from_string(subject_template).render(**variables)
        body = _env.from_string(body_template).render(**variables)
    except Exception:
        logger.exception("Template render failed")
        return subject_template, body_template
    else:
        return subject, body
