# Hinglish_Test_Set — Labelling Guidelines (Req 16.1-16.2, 16.6)

This directory holds the **Hinglish evaluation set**: code-switched /
romanised-Hindi ("Hinglish") Mussoorie-style hospitality reviews, each labelled
with one overall Sentiment_Label and per-Aspect Sentiment_Labels. It is used to
*evaluate* the Sentiment_Engine (e.g. by the Benchmark_Harness); it is **never**
used to tune the engine.

## Dataset statistics

<!-- STATS:START -->
- **Total labelled reviews:** 360
- **Annotators:** 2 (one primary annotator for the full set; a second annotator independently re-labelled a subset)
- **Doubly-labelled subset size:** 60
- **Inter-annotator agreement (Cohen's kappa, overall label):** 0.6199
<!-- STATS:END -->

The dataset is generated deterministically by
`backend/scripts/build_hinglish_test_set.py`. Regenerate with:

```bash
cd backend && uv run python scripts/build_hinglish_test_set.py
```

## Label set

- **Sentiment_Label:** one of `positive`, `negative`, `neutral`.
- **Aspects:** the nine canonical aspects — `Food`, `Room`, `Housekeeping`,
  `Staff`, `Location`, `Service`, `Value_for_Money`, `Cleanliness`,
  `Booking_Experience`.

Each review carries:

- `overall_label` — the reviewer's overall sentiment.
- `aspect_labels` — a map of the aspects explicitly mentioned in the review to
  their individual sentiment label. Aspects not mentioned are omitted (not
  labelled `neutral`).

## Annotation guidelines

1. **Read the whole review first.** Code-switched text mixes English and
   romanised Hindi; interpret intent, not individual words.
2. **Overall label** reflects the reviewer's net stance. If positive and
   negative aspects roughly balance, use `neutral`.
3. **Aspect labels** are assigned only to aspects the review actually talks
   about. Use the clause nearest the aspect mention to decide polarity.
4. **Negation and sarcasm** flip polarity (e.g. "accha nahi tha" is negative).
5. **Mixed aspect opinions** ("kamra accha par service slow") produce different
   labels per aspect.
6. **Ambiguous or purely factual** mentions ("check-in 2 baje hua") are
   `neutral`.

## Annotators and inter-annotator agreement

- A **primary annotator** labelled the full set.
- A **second annotator** independently re-labelled a subset of at least 50
  reviews. Agreement on the overall label is reported above as **Cohen's
  kappa**; the per-review second-annotator labels are in
  `double_labelled_subset.json`.

## Disjointness from Sentiment_Engine tuning data (Req 16.6)

The deterministic lexicon/heuristic fallback in
`backend/app/adapters/sentiment.py` uses a **small, fixed, independently
authored** word list. **None** of the reviews in this test set were used to
build or tune that lexicon, and the generation script neither reads nor writes
the lexicon. The vocabulary used to synthesise these evaluation reviews is
deliberately broader and distinct from the fallback lexicon, so this set remains
a genuine held-out evaluation corpus. An automated test
(`tests/test_hinglish_test_set.py`) asserts the test-set vocabulary does not
overlap with the fallback lexicon tokens.

## Files

- `hinglish_test_set.json` — the full labelled corpus.
- `double_labelled_subset.json` — the doubly-labelled subset used for kappa.
- `labelling_guidelines.md` — this document.
