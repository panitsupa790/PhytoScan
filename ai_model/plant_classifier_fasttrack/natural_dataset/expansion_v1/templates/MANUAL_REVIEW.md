# Manual review workflow

1. Import does not approve labels. Complete every metadata field first.
2. Run `review` and inspect every contact sheet.
3. In `manual_review_manifest.csv`, set:
   - species_confirmed: yes/no/uncertain
   - leaf_visible: yes/no
   - image_quality: good/acceptable/reject
   - natural_scene_confirmed: yes/no
   - license_verified: yes/no
   - review_decision: approved/rejected/uncertain
4. Review every `phash_similarity_only_review_required` pair and set a pair decision.
5. `split` fails closed while any approved image has unresolved metadata, label, license, quality, or duplicate status.
6. Never open the protected Locked Test manifest during model development.
