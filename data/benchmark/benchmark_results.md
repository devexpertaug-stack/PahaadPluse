# Hinglish Accuracy Benchmark

- Test set size: **360** reviews
- Seed: **20240601** (idempotent for a fixed seed, Req 16.8)

## Macro-F1 by system (95% bootstrap CI)

| System | Overall sentiment | Aspect detection | Aspect sentiment |
| --- | --- | --- | --- |
| PahadPulse Sentiment_Engine | 0.140 [0.121, 0.161] | 0.632 [0.606, 0.655] | 0.161 [0.147, 0.174] |
| Generic English lexicon (off-the-shelf) | 0.140 [0.121, 0.161] | 0.915 [0.903, 0.927] | 0.163 [0.152, 0.172] |
| Plain-LLM zero-shot (mock) | 0.699 [0.651, 0.742] | 0.915 [0.903, 0.927] | 0.527 [0.500, 0.557] |
