import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import generate_ppt
from scripts.md_to_plan import parse_directive, parse_slides
from scripts.template_analyzer import assign_layouts, render_prompt_from_template


def test_md_plan_accepts_template_page_types():
    for page_type in ("agenda", "section", "quote", "closing", "other"):
        assert parse_directive(page_type) == (page_type, None)

    slides = parse_slides("## 1. [agenda, layout=agenda-numbered-list] 议程\n- 第一项\n")
    assert slides[0]["page_type"] == "agenda"
    assert slides[0]["layout_id"] == "agenda-numbered-list"


def test_assign_layouts_prefers_unused_layouts_for_same_page_type():
    profile = {
        "layouts": [
            {"id": "cover", "page_type": "cover", "reuse_friendly": False},
            {"id": "content-a", "page_type": "content", "reuse_friendly": True},
            {"id": "content-b", "page_type": "content", "reuse_friendly": True},
            {"id": "content-c", "page_type": "content", "reuse_friendly": False},
        ]
    }
    slides = [
        {"slide_number": 1, "page_type": "cover"},
        {"slide_number": 2, "page_type": "content"},
        {"slide_number": 3, "page_type": "content"},
        {"slide_number": 4, "page_type": "content"},
    ]

    assigned = assign_layouts(slides, profile)

    assert [assigned[n]["id"] for n in [1, 2, 3, 4]] == [
        "cover",
        "content-a",
        "content-b",
        "content-c",
    ]


def test_template_layout_variation_metadata_enters_prompt():
    profile = {"global_style": "深蓝科技风", "layouts": []}
    layout = {
        "id": "content-split",
        "page_type": "content",
        "summary": "左侧短列表，右侧斜切图片栏",
        "visual_signature": "右侧斜切图片栏",
        "content_capacity": {"items": "3-5 short bullets"},
        "best_for": ["feature list", "overview"],
        "avoid_for": ["dense table"],
        "variation_tags": ["split", "image-right"],
        "json_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "页面标题"},
            },
        },
    }

    prompt = render_prompt_from_template(profile, layout, {"title": "能力总览"})

    assert "右侧斜切图片栏" in prompt
    assert "3-5 short bullets" in prompt
    assert "feature list" in prompt
    assert "dense table" in prompt
    assert "image-right" in prompt


def test_template_layout_profile_is_saved_without_manual_slide_spec():
    layout = {
        "id": "agenda-numbered-list",
        "page_type": "agenda",
        "summary": "左侧大标题，右侧编号议程列表",
        "visual_signature": "large agenda number rail",
        "content_capacity": {"items": "4-6 short agenda items"},
        "best_for": ["agenda", "overview"],
        "avoid_for": ["dense tables"],
        "variation_tags": ["numbered-list", "two-column"],
        "external_image_slots": [{"id": "photo", "bbox": [0.6, 0.2, 0.3, 0.5]}],
        "reuse_friendly": True,
        "reference_image": "/tmp/template/page-02.png",
    }

    spec = generate_ppt.attach_template_layout_profile(None, layout)

    assert spec["layout"] == "模板 agenda-numbered-list：左侧大标题，右侧编号议程列表"
    profile = spec["template_layout_profile"]
    assert profile["id"] == "agenda-numbered-list"
    assert profile["page_type"] == "agenda"
    assert profile["visual_signature"] == "large agenda number rail"
    assert profile["external_image_slots"] == [{"id": "photo", "bbox": [0.6, 0.2, 0.3, 0.5]}]
    assert "reference_image" not in profile
