# Verification

Run from the repository root with Python 3.9 or newer.

## Full offline verification

```bash
python3 -m unittest discover -s tests -v
python3 evaluate.py --output evaluation/results.json
git diff --exit-code -- evaluation/results.json
```

Expected properties:

- all automated tests pass;
- the evaluator exits `0`;
- `fixture_count` and `passed` are both `20`;
- `all_routes_matched` is `true`;
- `automatic_sends` is `0`; and
- regenerating the result produces no diff.

## Local page

```bash
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/`. Check the three visible case narratives, route
filters, 20-case result link, captioned video, transcript, synthetic-data label,
non-affiliation disclaimer, and mobile layout.

## CI

`.github/workflows/ci.yml` runs the test suite, regenerates the fixture result in
a temporary path, and diffs it against the committed evidence. It uses no model
key, platform credential, or network-dependent application test.

## Environment configuration

No `.env.example` is included because the implemented path reads no environment
variables. Adding placeholder model or platform keys would imply an integration
that does not exist.
