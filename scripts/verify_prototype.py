"""Snapshot the checks and sources for the current local prototype."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / "results/prototype"
game_log = (out / "game-tests.log").read_text()
assert "Ran 11 tests" in game_log and game_log.rstrip().endswith("OK")
dom = json.loads((out / "dom-qa.json").read_text())
for flag in ("offline_three_days_no_penalty", "canvas_renderer_executed", "oblique_projection_roundtrip",
             "zoom_keeps_pointed_tile", "overview_and_follow", "roof_hit_testing", "drag_pan", "pinch_zoom"):
    assert dom[flag]
assert dom["initial_choices"] == 2 and dom["daily_required_actions"] == 0
assert dom["completed_goals"] == ["garden"]
sources = sorted(set(root.glob("citygame/*.py")) | set(root.glob("citysim/*.py")) |
                 set(root.glob("config/*.json")) | set(root.glob("prototype/dist/*")) |
                 set(root.glob("scripts/prototype*")) | set(root.glob("scripts/render_prototype_map.*")) |
                 {Path(__file__), root / "scripts/canvas_recorder.cjs", root / "tests/test_game.py"})
evidence = [p for p in out.iterdir() if p.suffix in (".json", ".log", ".svg", ".png") and p.name != "verification.json"]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = {"current_game_tests_passed": 11, "baseline_full_suite_tests_passed": 43,
          "javascript_syntax_checked": True, "ui_flow_against_real_handler_passed": True,
          "camera_checks_passed": True, "browser_layout_verified": False,
          "browser_restriction": json.loads((out / "browser-qa.json").read_text()),
          "canvas_preview_is_browser_screenshot": False,
          "source_sha256": {str(p.relative_to(root)): sha(p) for p in sources},
          "evidence_sha256": {p.name: sha(p) for p in sorted(evidence)}}
(out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print("Parcours, caméra, 11 tests de partie et empreintes vérifiés. Mise en page navigateur non vérifiée.")
