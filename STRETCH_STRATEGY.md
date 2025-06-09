# Stretch Strategy – Toward Production-grade Multi-View Engineering Drawings

## 0. Project Recap
* **Mission** – Convert natural-language prompts into realistic, standards-compliant engineering drawings and their ground-truth JSON for computer-vision evaluation.
* **Phases 1-3 (Complete)** – Primitive renderer → AI Planner → Semantic feature engine.
* **Phases 4-6 (Complete)** – Parametric feature library, auto-dimensioner, robustness, CI/CD, dataset generator.

> Outcome so far: 2-D single-view drawings with correct geometry, layers, symbols and basic dimensions.

## 1. Stretch Goal
Deliver **multi-view, sectioned, hatch-filled CAD sheets** (ISO A-size) that visually match professional shop drawings, including:
* Front / top / right orthographics + isometric.
* Hidden-line removal, centre-lines, section views.
* Full title-block, border, revision table.
* Line-weights & CTB ready for plotting.
* Optional "messy scan" raster export for CV stress-tests.

## 2. Technical Gaps
| Area | Gap | Required Capability |
|------|-----|----------------------|
| 3-D Kernel | None in current stack | Build solid from feature list; Boolean ops; section planes. |
| Projection | Only 2-D primitives | Hidden-line removal, edge classification (visible/hidden/section). |
| View Layout | Single model-space view | Paper-space layout with border + auto-scaled views. |
| Section & Hatch | Not supported | Generate cut faces + standard hatch patterns. |
| Dimensioning | Edge-level 2-D | Map 3-D sizes/positions into each projected view; leader notes. |
| Noise Simulation | Simple blur | Blueprint filter, paper grain, streaks, rotation, fold marks. |

## 3. Road-map & Milestones
### Milestone 1 – 3-D Core (2 weeks)
1. Adopt **OCP (python-occ)** as solid kernel (`SolidBuilder`).
2. Implement feature → OCC operations (plate, hole, slot, fillet, chamfer…).
3. Produce single hidden-line-removed ISO view → DXF layer mapping.
**Exit test:** Plan with 5 features renders isometric view; area diff <1 % vs 2-D.

### Milestone 2 – Multi-View Sheet (3 weeks)
1. Orthographic projection (front/top/right).
2. Paper-space border + title-block (A3 & A4).  
3. Auto-scale & place 4 views; generate view labels.
**Exit test:** Four-view sheet of reference bracket (PNG hash baseline).

### Milestone 3 – Sections & Hatching (2 weeks)
1. Extend schema – `section_views` array (plane + label).
2. Cut solid, hatch faces (`ANSI31`, 2.5 mm).  
3. Show section arrows in parent view.
**Exit test:** Half-section view passes CI visual diff; hatch layer correct.

### Milestone 4 – Dimensioner v2 (3 weeks)
1. Baseline & ordinate chains, radial dims, thread call-outs.  
2. Bolt-circle note generator.  
3. Layer + style table (ISO/ASME switch).
**Exit test:** Auto-dimension coverage ≥95 % on 20-part suite.

### Milestone 5 – Presentation Polish (1 week)
1. Line-weight CTB + linetype file.  
2. "Messy blueprint" filter (blur, jitter, grain, rotation).  
3. Final QA checklist script.
**Exit test:** Human drafter rates ≥90 % "shop-ready"; noise realism survey ≥4/5.

## 4. KPI Dashboard (Stretch Phase)
| Metric | Target | Script |
|--------|--------|--------|
| Solid build success | 100 % plans build BREP | `tests/solid_build.py` |
| Hidden-line accuracy | Edge classification ≥98 % | `tests/hlr_compare.py` |
| Dimension coverage | ≥95 % | `tests/dim_coverage.py` |
| Section hatch compliance | 100 % faces hatched layer HATCH | `tests/section_hatch.py` |
| View-layout overlap | 0 overlaps >1 mm | `tests/layout_check.py` |
| Noise realism score | ≥4.0 / 5 | human survey |

CI will block on any KPI regression.

## 5. Resources & Risks
| Item | Estimate | Mitigation |
|------|----------|------------|
| OCP complexity | 6 MB wheel, steep API | Use CadQuery wrappers; start with simple primitives. |
| HLR performance | Large models slow | Cache edges, limit tessellation density. |
| Auto-dimension heuristics | False overlaps | Use network-flow optimisation to space dims; fallback manual marks in JSON. |
| Licensing | OCC LGPL, CadQuery Apache | Confirm compatibility; include NOTICE. |

## 6. Team Allocation
* **Lead Dev (1 FTE)** – geometry & projection.
* **CAD Standards Engineer (0.5 FTE)** – dimension rules, title-block.
* **QA / DevOps (0.25 FTE)** – CI, KPI scripts.
Duration ≈ **9 person-weeks**.

## 7. Immediate Next Action
Create `solidbuilder_ocp.py`, implement plate + through-hole, and add `--solid-view` flag to `generator.py` for proof-of-concept isometric projection.

---
*Document compiled : 2025-06-09* 