import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import generate_ppt
from scripts.template_analyzer import assign_layouts, render_prompt_from_template


def test_load_style_layout_profile_sidecar(tmp_path):
    style_path = tmp_path / "sample-style.md"
    style_path.write_text(
        "# Sample\n\n## 基础提示词模板\n\nBASE STYLE PROMPT\n",
        encoding="utf-8",
    )
    sidecar_path = tmp_path / "sample-style.layouts.json"
    sidecar_path.write_text(
        json.dumps(
            {
                "version": "2",
                "style_id": "sample-style",
                "global_style": "Concise style summary",
                "layouts": [
                    {
                        "id": "content-two-cards",
                        "page_type": "content",
                        "summary": "Two card content layout",
                        "visual_signature": "two cards",
                        "content_capacity": {"items": "2 short cards"},
                        "best_for": ["two key points"],
                        "variation_tags": ["cards"],
                        "reuse_friendly": True,
                        "json_schema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "items": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    profile = generate_ppt.load_style_layout_profile(str(style_path), "BASE STYLE PROMPT")

    assert profile is not None
    assert profile["source"] == "sample-style.layouts.json"
    assert profile["style_id"] == "sample-style"
    assert "BASE STYLE PROMPT" in profile["global_style"]
    assert "Concise style summary" in profile["global_style"]
    assert profile["layouts"][0]["id"] == "content-two-cards"
    assert profile["layouts"][0]["reference_image"] is None


def test_style_layout_profile_drives_builtin_style_prompt(tmp_path):
    style_path = tmp_path / "sample-style.md"
    style_path.write_text("# Sample\n\n## 基础提示词模板\n\nBASE STYLE PROMPT\n", encoding="utf-8")
    (tmp_path / "sample-style.layouts.json").write_text(
        json.dumps(
            {
                "version": "2",
                "style_id": "sample-style",
                "global_style": "Concise style summary",
                "layouts": [
                    {
                        "id": "content-a",
                        "page_type": "content",
                        "summary": "Left text with right image block",
                        "visual_signature": "right image block",
                        "content_capacity": {"items": "3 bullets"},
                        "best_for": ["feature list"],
                        "avoid_for": ["dense table"],
                        "variation_tags": ["split", "image-right"],
                        "reuse_friendly": True,
                        "json_schema": {
                            "type": "object",
                            "properties": {"title": {"type": "string"}},
                        },
                    },
                    {
                        "id": "content-b",
                        "page_type": "content",
                        "summary": "Three card grid",
                        "visual_signature": "three cards",
                        "reuse_friendly": True,
                        "json_schema": {
                            "type": "object",
                            "properties": {"title": {"type": "string"}},
                        },
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    profile = generate_ppt.load_style_layout_profile(
        str(style_path),
        generate_ppt.load_style_template(str(style_path)),
    )
    slides = [
        {"slide_number": 1, "page_type": "content", "content": "第一页"},
        {"slide_number": 2, "page_type": "content", "content": "第二页"},
    ]
    assigned = assign_layouts(slides, profile)
    prompt = render_prompt_from_template(profile, assigned[1], {"title": "第一页"})

    assert assigned[1]["id"] == "content-a"
    assert assigned[2]["id"] == "content-b"
    assert "BASE STYLE PROMPT" in prompt
    assert "right image block" in prompt
    assert "3 bullets" in prompt
    assert "image-right" in prompt


def test_real_eco_green_layout_bank_loads():
    style_path = ROOT / "styles" / "eco-green-business-plan.md"

    profile = generate_ppt.load_style_layout_profile(
        str(style_path),
        generate_ppt.load_style_template(str(style_path)),
    )

    assert profile is not None
    assert profile["style_id"] == "eco-green-business-plan"
    assert len(profile["layouts"]) >= 8
    assert {layout["page_type"] for layout in profile["layouts"]} >= {
        "cover",
        "agenda",
        "section",
        "content",
        "data",
        "quote",
        "closing",
    }
    assert all("visual_signature" in layout for layout in profile["layouts"])


def test_all_builtin_styles_have_loadable_layout_banks():
    style_paths = sorted((ROOT / "styles").glob("*.md"))
    assert style_paths

    for style_path in style_paths:
        sidecar = style_path.with_suffix(".layouts.json")
        assert sidecar.exists(), f"missing layout sidecar for {style_path.name}"

        profile = generate_ppt.load_style_layout_profile(
            str(style_path),
            generate_ppt.load_style_template(str(style_path)),
        )

        assert profile is not None, f"sidecar did not load: {sidecar.name}"
        assert profile["style_id"], f"missing style_id in {sidecar.name}"
        assert len(profile["layouts"]) >= 6, f"too few layouts in {sidecar.name}"
        page_types = {layout["page_type"] for layout in profile["layouts"]}
        assert {"cover", "content", "data"}.issubset(page_types), sidecar.name
        for layout in profile["layouts"]:
            assert layout["id"], f"layout missing id in {sidecar.name}"
            assert layout["summary"], f"{layout['id']} missing summary in {sidecar.name}"
            assert layout.get("visual_signature"), f"{layout['id']} missing visual_signature in {sidecar.name}"
            assert layout.get("content_capacity"), f"{layout['id']} missing content_capacity in {sidecar.name}"
            assert isinstance(layout.get("variation_tags"), list), f"{layout['id']} invalid variation_tags in {sidecar.name}"
