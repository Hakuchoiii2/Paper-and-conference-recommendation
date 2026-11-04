# Gold400 QLoRA: paired V-recall test

Gold400 was purposively selected and previously inspected during pipeline development; this is a new paper-level training split, not an independent external holdout.

| Arm | Precision | Recall | F1 | Macro F1 | Fallback |
|---|---:|---:|---:|---:|---:|
| base-V-recall | 22.5519 | 30.2789 | 25.8503 | 25.9651 | 4 |
| gold400-QLoRA-V-recall | 63.1673 | 70.7171 | 66.7293 | 67.6692 | 3 |
