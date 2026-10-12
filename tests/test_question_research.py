import json
from pathlib import Path


DATASET = Path(__file__).parents[1] / "data" / "examples" / "corolla-2024-user-questions.json"


def test_car6_question_research_is_complete_and_model_ready():
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    categories = {item["id"] for item in payload["categories"]}
    questions = payload["questions"]
    follow_ups = payload["follow_up_questions"]
    question_ids = {item["id"] for item in questions}

    assert len(questions) >= 30
    assert len(question_ids) == len(questions)
    assert {item["priority"] for item in questions} <= {"P0", "P1", "P2"}
    assert all(item["category"] in categories for item in questions)
    assert all(item["question"].endswith("?") for item in questions)
    assert all(item["parent_id"] in question_ids for item in follow_ups)
    assert all(item["requires_context"] is True for item in follow_ups)
    assert any(item["variant_sensitive"] for item in questions)
    assert {item["system"] for item in questions} >= {
        "maintenance", "engine", "tires", "multimedia", "driver_assistance"
    }
