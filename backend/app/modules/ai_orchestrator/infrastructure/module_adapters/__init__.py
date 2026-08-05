"""One concrete `WorkflowExecutorPort` implementation per orchestrated
`WorkflowModule` — the seam between this module's own generic
`WorkflowExecutionInput` and each of the twelve peer AI modules' own,
mutually-incompatible strongly-typed input value objects (see `domain
/value_objects.py::WorkflowExecutionInput`'s own module docstring for
why that bundle is deliberately generic).

Every adapter in this package follows the same three-part shape:

1. `check_prerequisites(bundle)` — returns missing-prerequisite reasons
   (empty tuple = this adapter's own peer module has enough information
   in `bundle` to run). An adapter never fabricates data to satisfy a
   peer module's own required field; if `bundle` genuinely lacks what
   that field needs (e.g. `RiskStratificationInput.vital_signs` needs
   at least one parseable vital sign; `PatientEducationInput` needs a
   non-empty `diagnoses` *and* a non-empty `current_medications`;
   `LabInterpretationInput.lab_values` and the radiology/pathology
   adapters' own `report_text` need non-empty free-text findings), the
   step is skipped by `WorkflowExecutorService`, never run against
   invented input.
2. `execute(bundle, context)` — translates `bundle` (plus `context`,
   the already-completed upstream steps' own `raw_text` output, keyed
   by `WorkflowModule` — see `WorkflowStepResult.summary`'s own
   docstring) into this adapter's own peer module's strongly-typed
   input, constructed with that peer module's own **general/outpatient-
   equivalent** setting member (every one of the twelve peer modules'
   own "setting" enum carries an `OUTPATIENT`-or-equivalent general
   member — this orchestrator has no finer-grained, per-step
   configuration surface of its own, so this is the one deliberately
   uniform choice across all twelve adapters), calls that peer's own
   public facade (constructed via that peer module's own `container.py`
   factory function — the same "import a peer module's `public/`
   package, plus its `container.py` factory function to construct one"
   precedent every prior AI module's own use case establishes for its
   own, single genuine peer-module dependency, replicated twelve times
   here since genuinely invoking peer facades is this module's entire
   purpose), and returns a `WorkflowStepResult`.
3. `confidence_score`/`summary` are read directly off the peer's own
   `Generated*.result`/`.session` — `summary` is always that result's
   own `raw_text` field (present on every one of the twelve peer
   modules' own result types), never a second `render_*` call, so no
   adapter needs to know anything about a peer's own rendering pipeline
   (see `domain/value_objects.py::WorkflowStepResult`'s own docstring).
   `confidence_score` is `None` on the four adapters
   (`clinical_note`/`soap_note`/`icd10_coding`/`prescription`) whose own
   peer result type carries no such field at all — a documentation/
   coding-suggestion/prescription-drafting tool has no equivalent
   "AI-reported confidence" the way the eight diagnostic/interpretation
   modules do, so `None` here is accurate, not a missing value.
"""
