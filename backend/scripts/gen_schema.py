"""Generate the published Review_Record JSON schema from the pydantic model.

Run with: ``uv run python scripts/gen_schema.py``. Keeps
``app/schemas/review_record.schema.json`` in sync with
:class:`app.models.review.ReviewRecord` (Req 3.4, 3.8).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models.review import ReviewRecord

OUT = Path(__file__).resolve().parents[1] / "app" / "schemas" / "review_record.schema.json"


def main() -> None:
    schema = ReviewRecord.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://pahadpulse.example/schemas/review_record.schema.json"
    schema["title"] = "Review_Record"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
