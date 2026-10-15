/-
  Acceptance contract for the dial.

  Lean checks this decision table. The Gemma parameters, the adapter
  tensors, and the engine's floating-point division are not inputs.
  A model string is accepted only when it is a declaration and the
  compiler exit is 0.
-/

inductive Verdict where
  | unscored
  | missingBar
  | outside
  | inside
  deriving DecidableEq, Repr

/-- Killed unless the score sits inside a published bar. -/
def killed : Verdict → Bool
  | .inside => false
  | _ => true

/-- Inside the bar is consistency with the measurement. It is not sent. -/
def send : Verdict → Bool
  | _ => false

def reasonName : Verdict → String
  | .unscored => "unscored"
  | .missingBar => "no_published_uncertainty"
  | .outside => "outside_published_uncertainty"
  | .inside => "inside_published_uncertainty"

theorem kill_table :
    killed .unscored = true ∧
    killed .missingBar = true ∧
    killed .outside = true ∧
    killed .inside = false ∧
    send .unscored = false ∧
    send .missingBar = false ∧
    send .outside = false ∧
    send .inside = false := by
  decide

theorem only_inside_is_kept (v : Verdict) : killed v = false ↔ v = .inside := by
  cases v <;> decide

theorem kept_is_still_not_sent (v : Verdict) : killed v = false → send v = false := by
  cases v with
  | unscored => intro h; cases h
  | missingBar => intro h; cases h
  | outside => intro h; cases h
  | inside => intro _; rfl

/-- Published z = numer/denom is inside only when the denominator is positive and numer ≤ denom. -/
def within (numer denom : Nat) : Bool :=
  denom != 0 && decide (numer ≤ denom)

theorem boundary_is_inside : within 1 1 = true := rfl

theorem above_one_is_outside : within 2 1 = false := rfl

theorem half_is_inside : within 1 2 = true := rfl

theorem missing_denom_is_outside (n : Nat) : within n 0 = false := rfl

inductive TrainTarget where
  | recordedStatement
  | closerToCenter
  deriving DecidableEq

def allowedTarget : TrainTarget → Bool
  | .recordedStatement => true
  | .closerToCenter => false

theorem training_does_not_reward_the_center :
    allowedTarget .closerToCenter = false := rfl

/-- A formula proposal and a Lean declaration are different inputs to the checker. -/
inductive Line where
  | proposal
  | declaration
  deriving DecidableEq, Repr

def isLeanDeclaration : Line → Bool
  | .proposal => false
  | .declaration => true

structure Emission where
  line : Line
  exitCode : Option Nat

def leanAccepts (e : Emission) : Bool :=
  isLeanDeclaration e.line && e.exitCode == some 0

theorem proposal_is_not_a_declaration : isLeanDeclaration .proposal = false := rfl

theorem exit_code_alone_does_not_accept :
    leanAccepts { line := .proposal, exitCode := some 0 } = false := rfl

theorem a_declaration_can_be_submitted : isLeanDeclaration .declaration = true := rfl

theorem acceptance_is_declaration_and_exit (e : Emission) :
    leanAccepts e = true ↔
      isLeanDeclaration e.line = true ∧ (e.exitCode == some 0) = true := by
  unfold leanAccepts
  exact Iff.of_eq (Bool.and_eq_true _ _)
