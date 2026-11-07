# Plant Classifier Notebook/Backend Parity Audit

Scope: Validation only. This audit does not select or modify thresholds and does not reopen Test.

- Model SHA-256 equal: `True`
- Class mapping equal: `True`
- Manifest labels match plant column: `True`
- Notebook-compatible errors: `7`
- Backend-before-fix errors: `2`
- Top-1 disagreements: `7`

Conclusion: The model, class mapping, manifest row order, and labels match. The preprocessing implementation differs and changes top-1 predictions near decision boundaries.
