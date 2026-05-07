.PHONY: demo test golden-update baseline-update showcase replay-index

demo:
	python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui && python scripts/run_match_matrix.py --out data/match_matrix_report.json && python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json && python -m http.server 8000

test:
	python -m pytest -q

golden-update:
	python scripts/regenerate_golden_replays.py && python -m pytest -q

baseline-update:
	python scripts/run_comparison_report.py --team-a data/teams/team_a_static_baseline.json --team-b data/teams/team_b_adaptive_counter.json --seeds 42,99,202,311,404,515,628,733,841,956,1063 --out data/baseline/comparison_report.json && python -m pytest -q

showcase:
	python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui

replay-index:
	python scripts/build_replay_index.py
