# Visual Sanity Review

The three class contact sheets were inspected at their generated resolution.
This review checks implementation behavior and obvious artifacts only. It does
not rank variants or claim classification improvement.

| Variant | Observed behavior | Severe artifact check |
|---|---|---|
| P0 | Aspect ratio and leaf morphology are preserved with white padding. | No severe distortion or unexpected color shift observed. |
| P1 | Fine texture is smoothed as expected from a mild `3x3` median filter; major veins and lesions remain visible. | No severe over-smoothing or lesion removal observed in the fixed sample. |
| P2 | Luminance separation increases mildly while lesion colors remain plausible. | No obvious channel swap, severe clipping, or dramatic color shift observed. |
| P3 | Fine edges and lesion boundaries become slightly crisper. | No strong halo or ringing artifact observed. |

No winner was selected. Model experiments on train and validation data are
required before any preprocessing variant can be chosen.
