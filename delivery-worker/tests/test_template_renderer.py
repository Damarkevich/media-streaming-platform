"""Tests for src.services.template_renderer."""


class TestRender:
    def test_renders_subject_and_body(self):
        from src.services.template_renderer import render

        subject, body = render(
            "Hello {{ name }}",
            "<p>Dear {{ name }}</p>",
            {"name": "Alice"},
        )

        assert subject == "Hello Alice"
        assert body == "<p>Dear Alice</p>"

    def test_renders_with_multiple_variables(self):
        from src.services.template_renderer import render

        subject, body = render(
            "Top {{ n }} films for {{ user }}",
            "<ul>{% for f in films %}<li>{{ f }}</li>{% endfor %}</ul>",
            {"n": 10, "user": "Bob", "films": ["Film A", "Film B"]},
        )

        assert "10" in subject
        assert "Bob" in subject
        assert "Film A" in body
        assert "Film B" in body

    def test_returns_raw_templates_on_render_error(self):
        from src.services.template_renderer import render

        bad_subject = "{{ unclosed"
        bad_body = "{{ also_bad"

        subject, body = render(bad_subject, bad_body, {})

        assert subject == bad_subject
        assert body == bad_body

    def test_autoescape_prevents_xss(self):
        from src.services.template_renderer import render

        _, body = render(
            "Hi",
            "<p>{{ content }}</p>",
            {"content": "<script>alert(1)</script>"},
        )

        assert "<script>" not in body
        assert "&lt;script&gt;" in body

    def test_empty_variables(self):
        from src.services.template_renderer import render

        subject, body = render("Static subject", "<p>Static body</p>", {})

        assert subject == "Static subject"
        assert body == "<p>Static body</p>"
