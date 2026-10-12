# Risk_Scorer validation (held-out synthetic set)

- Seed: `20240601`
- Samples: 600 (221 positive)
- **ROC AUC: 0.8499**
- Expected calibration error (ECE): 0.0976

## Calibration

| Predicted bin | n | mean predicted | observed positive rate |
| --- | ---: | ---: | ---: |
| [0.0,0.1) | 0 | — | — |
| [0.1,0.2) | 138 | 0.198 | 0.065 |
| [0.2,0.3) | 86 | 0.255 | 0.081 |
| [0.3,0.4) | 85 | 0.347 | 0.306 |
| [0.4,0.5) | 104 | 0.436 | 0.356 |
| [0.5,0.6) | 60 | 0.548 | 0.6 |
| [0.6,0.7) | 47 | 0.648 | 0.681 |
| [0.7,0.8) | 42 | 0.753 | 0.881 |
| [0.8,0.9) | 24 | 0.855 | 0.958 |
| [0.9,1.0) | 14 | 0.936 | 1.0 |
