# Resume

Pickup note for math-si. Updated 2026-10-19. Read this before training
or scoring again.

The model proposes. The pinned engine computes. A published uncertainty
scores. Lean 4 checks a formal statement. The ledger records the try.
Nothing in the ledger has been sent, and nothing has been promoted into
the hub.

## Where things stand

The live dial in `dial/local_model.py` still loads `adapter/`. That is
epoch 1. The weights that currently say the twelve inside-bar expressions
are `adapter-epoch7/`. Switching the dial to epoch 7 has not been done.

Twelve published-bar rows sit inside z ≤ 1 under epoch 7. Nine of them are
the recorded formula as written. Matter-clustering `sigma_8` is the cleaned
product `psi_con*phi^(1-ln(phi))`. The two reionization rows are the
recorded absolute value spelled `phi*abs(Chaos) - ln(phi)`. That spelling
was also emitted on the sigma_8 scalar row, where it is outside the bar.

## Machine

HP Omen 35L, RTX 5070 12227 MiB, driver 595.95, compute 12.0, about 32 GB
RAM, Windows 11, Python 3.14.4. Base weights live at
`D:\models\gemma-4-E4B-it` and are not in git. Ollama is optional chat
through `ask.ps1` (`gemma4:latest`, thinking off, `127.0.0.1:11434`).
Ollama is not the trainer. A GGUF cannot carry this LoRA.

Stack that trained: torch 2.11.0+cu128, transformers 5.5.0, peft 0.18.1,
trl 1.0.0, bitsandbytes 0.49.2. QLoRA, 4-bit NF4, bf16 compute, double
quant, LoRA r=16, alpha=32, dropout 0.05, on language-model
`q_proj`, `k_proj`, `v_proj`, `o_proj` only. About 10.9 million trainable
parameters, 0.136% of the model. Batch 1, gradient accumulation 8,
max length 768.

Logged `train_loss` is about 8 times the per-token cross entropy because
TRL does not divide by the accumulation steps.

## Model facts that training depends on

Gemma 4 E4B, `google/gemma-4-E4B-it`, Apache 2.0. Text: vocab 262144,
hidden 2560, 42 layers, sliding window 512. `use_bidirectional_attention`
is null, so text-only chat does not need `mm_token_type_ids`. Text chat
must go through the tokenizer `apply_chat_template`. The processor
crashes on string content. Thinking stays off: `enable_thinking=False`.

Eighteen layers share keys and values. With `use_cache=False`, later
layers invent keys and the logits scramble. `dial/kv_share.py` installs
`ShareCache` on each `Gemma4TextAttention._fsot_share` whenever
`language.training` and `past_key_values is None`. Do not wrap generation
with that share. Do not clear `_fsot_share` in a `finally`.

## Rules that stay in force

The hub `C:\Users\damia\Desktop\FSOT-2.1-Lean` is read-only from this
project. Do not edit `vendor/fsot_compute.py`. Pin AEB2AD is the engine
pin. Do not mix pin D1D38A into it.

The training target is a recorded statement in the existing grammar. A
closer distance to a measured center is not a reward. A decimal
coefficient is a gate failure. An unweighted midpoint is a gate failure.
A name the engine does not know is unscored. Inside one published
standard uncertainty means consistency with that measurement. It does
not mean equality to the center, it does not raise a held-out count, and
it is not a send.

A missing published bar is a kill. Flat percent is recorded and is not a
second cutoff. `sota_typical_error_pct` and the hub's blanket biochem
and behavioral percents are not published bars. An arXiv abstract is a
location, not a sigma.

`send` and `promoted` stay false until Damian says otherwise.

## How a try works

1. `dial/prompt.py` builds one prompt: the rule, domain, name, property,
   measured value, and the published-bar lines from `dial/bars.py`.
   The recorded formula is not in the prompt.
2. Gemma emits one `PROPOSAL:` line. Greedy decoding.
3. `dial/engine.py` gates the text, then the pinned engine evaluates it.
4. `dial/score.py` computes z = percent error / published uncertainty
   percent. z ≤ 1 is inside. z > 1 is `outside_published_uncertainty`.
   No bar, or no z, is `no_published_uncertainty` or `unscored`.
5. `dial/run.py` appends the try to `ledger/attempts.jsonl`.

The gate rejects a decimal literal, an unweighted `(a+b)/2`, an unknown
name, an eval error, and any character the hub tokenizer would drop.
That last rule was added after epoch 5. `|` and `:` are in it. The hub
tokenizer silently deletes them, so a proposal that contains them is not
scored as the stripped text.

A formula string is not Lean. `lean_check.py` runs `lake env lean` with
the hub as the working directory, toolchain `leanprover/lean4:v4.31.0`.
`checks/Contract.lean` proves the kill table, that a kept row is still
not sent, that z = numer/denom is inside only for a positive denominator
and numer ≤ denom, and that a formula proposal is not a Lean acceptance.
`python -u checks\run_contract.py` compiled it with exit 0. Re-run that
before trusting a later edit of the kill.

## What the system was taught

The loss was always the recorded text, never a distance to a measurement.

Epoch 1, the full corpus, taught the proposal grammar and the recorded
formulas in `corpus/combined.jsonl` (11,030 rows: formula points, Lean
declarations, law and constants, and gate-kept tool rows). The gate had
kept 1,184 tool rows and dropped 1,049, mostly unknown names.

Epoch 2 continued that same corpus.

Epoch 3 repeated only the 45 rows that already had a published bar.

Epoch 4 repeated three recorded formulas the engine already placed inside
the bar, plus a light keep of the six that epoch 3 had recovered.

Epoch 5 added Lean declarations from the hub, the C++ balanced-ternary
notes and `trit.hpp` header from `FSOT-2.1-Cpp`, and the 64-codon trinary
map, and it stated the still-open rows as current statements with a kill
status. The fine-structure leaf was named as a different row. It was not
a target for those open rows.

Epoch 6 taught `psi_con*phi^(1-ln(phi))` for the `sigma_8` matter-clustering
row only, and kept the nine recorded passes. `psi_con` in the engine is
`1 - e^(-1)`.

Epoch 7 taught the legal spelling of two recorded formulas the gate had
been rejecting, and repeated the other open rows as their own statements.
`FSOT: phi*(e/pi)+1` is the label plus `phi*(e/pi)+1`. `|Chaos|` is
`abs(Chaos)`. Chaos in the engine is negative, so a bar the tokenizer
drops flips the sign and the reionization value comes out near −1.017.
`phi*abs(Chaos) - ln(phi)` is the recorded absolute value. It was not
copied from another row.

## Approaches, in order

1. Local Hugging Face training. Ollama was left as optional chat.
2. One full epoch on the recorded corpus. The model emitted legal
   `PROPOSAL:` lines and did not land on the measurements. Eight short
   recorded formulas were repeated exactly. Zero of eleven published-bar
   rows were inside z ≤ 1. Median model flat error was about 69 percent.
3. A kill metric. High error is a kill when it is outside the published
   uncertainty. A missing bar is also a kill. Thirty-seven usage proposals
   were logged: 9 outside, 2 unscored, 26 with no published uncertainty.
   None were sent.
4. Bar lookup. A percent enters the kill from the row's own sigma or from
   `literature_uncertainty_anchors.json`. The species catalog has centers
   and no uncertainty column. CODATA `allascii.txt` at
   `K:\FSOT-PublicData\open_science_large\codata\allascii.txt` has an
   uncertainty column for fundamental constants. The local arXiv snapshot
   is `D:\training data\arXiv Dataset\arxiv-metadata-oai-snapshot.json`.
   It is an abstract index. A scan found no ± next to acoustic impedance.
   The work-function ± values that were found do not match the catalog
   centers. They were not used as a kill percent.
5. A Lean acceptance contract for the kill table and for what counts as
   a declaration. The Gemma weights are not a term in that file.
6. Focused recovery of recorded formulas that the engine can already
   place inside a bar. That produced the nine recorded passes.
7. A source-and-open pass, aimed at the stuck fundamentals and at the
   trinary and Lean application text. It kept the nine and also emitted
   a `sigma_8` line whose bars and colons the tokenizer deleted.
8. A gate that rejects those dropped characters, then a pass that teaches
   the cleaned product on that one row.
9. Epoch 7 spelled `|Chaos|` as `abs(Chaos)` and dropped the `FSOT:` label
   on the dependency-length row. The absolute-value spelling is the
   recorded reionization formula. The label is not part of the math.

## Scored results

Epoch 7, greedy, 45 published-bar rows, `logs/epoch7_score.jsonl`.
Trained 228 steps at 5e-6 from `adapter-epoch6` on
`corpus/epoch7_cover.jsonl`. Logged train loss 5.078. Nothing was sent.
Twelve rows are inside. The ten from epoch 6 held. Two are new.

| Row | Expression the model said | z |
| --- | --- | --- |
| fine-structure constant | `1/(e^3*phi^4 - psi_con - (POOF*SUCTION)^2*(C_factor^2/P_base))` | 0.567 |
| inverse fine-structure | `e^3*phi^4 - psi_con - (POOF*SUCTION)^2*(C_factor^2/P_base)` | 0.538 |
| N_eff | `P_new·e·π + ln(φ)` | 0.285 |
| Planck 2018 w0, w0_cmb, w0_CMB | `−P_new·π/G` | 0.0006 |
| PantheonPlus w0 | `−P_new·π/G` | 0.761 |
| DESI 2024 BAO preview w0 | `−P_new·π/G` | 0.326 |
| dwarf-core radius r_c | `eta_eff*phi - poof` | 0.020 |
| sigma_8 matter clustering | `psi_con*phi^(1-ln(phi))` | 0.045 |
| tau reionization optical depth | `phi*abs(Chaos) - ln(phi)` | 0.240 |
| tau reionization scalar | `phi*abs(Chaos) - ln(phi)` | 0.0005 |

The reionization expression evaluates to 0.054397. The optical-depth
center is 0.0561, bar 12.67%, z 0.240. The scalar center is 0.0544, same
bar, z 0.0005. The recorded text is still `φ·|Chaos| − ln(φ)`. The `abs`
spelling is how the hub parser keeps the absolute value. It is not a new
coefficient.

That same expression was also said on `sigma_8` fsot_compute_scalar.
That row's recorded formula is still `|S_cosm|·S_quant + |Chaos|`. The
engine value 0.054397 against that row's center is z 126, outside. A pass
on reionization does not move to sigma_8.

`w0_bao` and `w0_BAO` now say their own recorded line `w0_cmb·(1 − G/π)`
instead of the passing w0 expression. `w0_cmb` is not an engine name, so
those rows stay unscored. DESI DR2 said `w0_cmb·(1 − ln(φ)/π)`, which is
not the recorded line. Mean dependency length said
`phi*(e/pi)+alpha_eff*(1-phi/sqrt(3))`. The recorded math
`phi*(e/pi)+1` is 2.400 against 2.3, z 0.768, and the model did not say
it. Deuterium said a superscript form the gate rejects. Electron g still
uses an unknown name.

Sixteen rows match their recorded text, including Bohr radius, Compton
wavelength, classical electron radius, and Bohr magneton. Those use `h`
or `m_e`, so they stay unscored.

Epoch 6, for comparison, is `logs/epoch6_score.jsonl`. Ten inside. Train
loss on that pass was 1.119. Nothing was sent. The engine value of the w0
expression is about −1.02998. The dwarf-core expression is 0.602 against a
measured 0.6. The sigma_8 product is 0.811372 against a measured 0.8111
and a 0.74% bar. Earlier files are `logs/epoch2_score.jsonl` through
`logs/epoch5_score.jsonl`. Epoch 2 had 0 of 45 inside. Epoch 3 recovered 6.
Epoch 4 reached 9. Epoch 5 kept those 9 and first showed the sigma_8
number, still wrapped in `|` and `::`.

## What is still open

These published-bar rows did not pass under epoch 7.

The mass and atomic constants, the g-factors, and several electromagnetic
constants use names the engine does not have, including `h`, `m_e`, and
`w0_cmb`. Repeating the recorded text cannot produce a z until the engine
knows the name. Do not add those names by editing the hub unless Damian
asks.

Mean dependency length's recorded math is `phi*(e/pi)+1`, which the engine
places at 2.400 against 2.3, z 0.768. Epoch 7 did not say that line.
Deuterium's recorded `1/(π⁴·e⁶)` is gate-legal and outside, z 4.48. Hubble
is unscored. DESI DR2 still is not its recorded statement. `w0_bao` and
`w0_BAO` say their recorded statement and stay unscored. The sigma_8
scalar row must not receive the reionization expression or the
matter-clustering product.

Acoustic impedance and work function still have no published percent in
the species catalog or the anchor file. They stay killed as
`no_published_uncertainty`.

Held-out recovery, one observable choosing the form and a second scoring
it, is not coded. The nine recorded passes were in the training file.

## Adapter versions

| Directory | What it is |
| --- | --- |
| `adapter/` | Epoch 1. The dial loads this. 1,379 steps, logged train loss 5.298, token accuracy 0.854. |
| `adapter-20step/` | A 20-step smoke. Not loaded. It emitted `1.0 * 10^(-4)`. |
| `adapter-epoch2/` | Second epoch of the full corpus. 1,379 steps, loss 3.989, accuracy 0.861. Zero published-bar passes. |
| `adapter-epoch3/` | 45 published-bar formulas, 360 steps, loss 8.163. Six inside. |
| `adapter-epoch4/` | The three recoverable formulas plus the six, 420 steps, loss 0.160. Nine inside. |
| `adapter-epoch5/` | Source, trinary, and open-problem text, 400 steps, loss 8.112. Nine inside, plus the raw sigma_8 line. |
| `adapter-epoch6/` | Cleaned sigma_8 product plus the nine, 240 steps, loss 1.119. Ten inside. |
| `adapter-epoch7/` | Legal reionization absolute value plus the open-row statements, 228 steps, loss 5.078. Twelve inside. The tau expression also landed on the sigma_8 scalar row, where it is outside. |

Checkpoints, optimizer states, and the copied `tokenizer.json` files are
gitignored. The base tokenizer comes from `D:\models\gemma-4-E4B-it`.

## How to resume

From `C:\Users\damia\Desktop\math si`:

```
python -u checks\run_contract.py
python -u checks\score_adapter.py --adapter adapter-epoch7 --out logs\epoch7_score.jsonl --source epoch7-score
python -u dial\run.py --self-test
```

The self-test appends one ledger line. The score script appends one ledger
line per row. Do not treat either as a promotion.

A new training run must use `--resume-adapter` and a new `--output-dir`.
`train_lora.py` refuses to resume into the same directory. The default
output is `adapter/`, which is the dial's epoch 1. Do not point a new run
at that directory.

The next useful question is a legal expression, with no stray characters,
for one still-open row, scored by the engine against that row's own
published bar. A pass on one row does not move to another row.
