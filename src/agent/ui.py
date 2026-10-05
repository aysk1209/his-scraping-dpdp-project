"""Where each instruction happens, read off the HIS as it was last crawled.

The registry says *what* to do -- open the module that holds these fields, press
the button that creates a patient, read this column -- and never what the screen
calls those things. This module supplies the words. Given the crawler's
navigation map it knows, for the HIS as it is today:

- which module holds a field (and whether on the list or only on the record page),
  by the field's *content*, so a module that was renamed, moved or split is
  still found;
- what each column is labelled on screen;
- which button performs an operation, by matching the labels the crawler read
  against a vocabulary of the names HIS releases give that operation.

So when an update renames "Billing & Accounts" to "Accounts", moves the payer to a
module of its own and calls "Generate invoice" "Create bill", the next crawl is
the whole fix: the same function renders new, correct instructions. What it
cannot place -- a button whose new name is outside the vocabulary, a field whose
new header nobody has mapped -- it does not guess at. The step is **withheld**,
with the reason, until a person confirms the mapping (``control_aliases`` here,
``field_aliases`` in the crawler).

Without a map the agent still answers, in the HIS model's own vocabulary (layer
names, field names, canonical button names): that is how it worked before there
was a portal to crawl.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable, Literal

from pydantic import BaseModel, Field

from data_synthetic.catalogue import FIELD_CATALOGUE
from interop.layers import HISLayer

if TYPE_CHECKING:                                   # the crawler needs a browser; the agent does not
    from extraction.tier2.navigation import NavigationMap


# --------------------------------------------------------------------------- #
# The button vocabulary
# --------------------------------------------------------------------------- #

class Action(BaseModel, frozen=True):
    """One operation a HIS offers as a button, and the names releases give it."""

    id: str
    label: str                                      # canonical name, used when there is no map
    synonyms: tuple[str, ...] = ()                  # other names it goes by on screen

    def names(self) -> tuple[str, ...]:
        return (self.label, *self.synonyms)


def _a(id: str, label: str, *synonyms: str) -> Action:
    return Action(id=id, label=label, synonyms=synonyms)


ACTIONS: dict[str, Action] = {a.id: a for a in [
    # patient administration
    _a("create_patient", "New patient", "Add registration", "Register patient", "Add patient",
       "New registration", "Create patient"),
    _a("edit_details", "Edit details", "Update demographics", "Update details", "Edit patient",
       "Modify details", "Edit"),
    _a("mark_arrived", "Mark arrived", "Check-in", "Check in", "Arrived", "Mark arrival"),
    _a("book_appointment", "Book appointment", "New appointment", "Schedule appointment",
       "Add appointment", "Book"),
    _a("reschedule", "Reschedule", "Change appointment", "Move appointment", "Reschedule appointment"),
    _a("cancel_appointment", "Cancel appointment", "Cancel booking", "Cancel visit"),
    _a("allocate_bed", "Allocate bed", "Assign bed", "Bed allocation", "Admit"),
    _a("transfer", "Transfer", "Transfer ward", "Change ward", "Transfer patient", "Move bed"),
    _a("discharge", "Discharge", "Discharge patient", "Release bed"),
    _a("ward_census", "Ward census", "Occupancy report", "Census", "Bed occupancy", "Census report"),
    _a("withdraw_consent", "Record consent withdrawal", "Withdraw consent", "Revoke consent",
       "Consent withdrawal"),
    _a("privacy_request", "Log privacy request", "Data protection request", "Privacy request",
       "Data request", "Data principal request", "Rights request"),
    # clinical
    _a("record_dose", "Record dose given", "Administer", "Record administration", "Give dose",
       "Chart dose"),
    _a("add_allergy", "Add allergy", "New allergy", "Record allergy"),
    _a("ready_for_discharge", "Ready for discharge", "Mark fit for discharge", "Fit for discharge",
       "Discharge ready"),
    # ancillary / departmental
    _a("new_lab_request", "New lab request", "Order test", "Lab order", "Request test", "New order"),
    _a("record_observation", "Record observation", "Add vitals", "Record vitals", "New observation",
       "Enter vitals"),
    # administrative / financial
    _a("open_account", "Open account", "New account", "Create account"),
    _a("check_eligibility", "Check eligibility", "Verify coverage", "Eligibility check",
       "Check coverage"),
    _a("post_charge", "Post charge", "Add charge", "Enter charge"),
    _a("generate_invoice", "Generate invoice", "Create bill", "Generate bill", "Raise bill",
       "Final bill"),
    _a("record_settlement", "Record settlement", "Mark settled", "Record payment", "Settle"),
]}

_WORD = re.compile(r"[a-z0-9]+")


def normalise(label: str) -> str:
    """Case, spacing and punctuation do not distinguish two button names."""

    return " ".join(_WORD.findall(label.lower()))


_BY_NAME: dict[str, str] = {normalise(n): a.id for a in ACTIONS.values() for n in a.names()}


def match_control(label: str, aliases: dict[str, str] | None = None) -> str | None:
    """The operation a button performs, judged by its label -- or None if unknown.

    Exact matches only, after normalising: "Discharge" is not "Ready for
    discharge". ``aliases`` (label -> action id) is where a hospital confirms a
    name the vocabulary does not know; it wins over the vocabulary.
    """

    key = normalise(label)
    for shown, action in (aliases or {}).items():
        if normalise(shown) == key:
            return action
    return _BY_NAME.get(key)


# --------------------------------------------------------------------------- #
# Words for things when there is no map
# --------------------------------------------------------------------------- #

LAYER_NAMES: dict[HISLayer, str] = {
    HISLayer.PATIENT_ADMINISTRATION: "Patient Administration",
    HISLayer.CLINICAL_EHR: "the clinical record",
    HISLayer.ANCILLARY_DEPARTMENTAL: "Departmental Orders",
    HISLayer.ADMINISTRATIVE_FINANCIAL: "Billing",
    HISLayer.INFRASTRUCTURE_INTEGRATION: "the integration log",
}

_FIELD_WORDS = {
    "mrn": "MRN", "insurance_policy_no": "policy number", "date_of_birth": "date of birth",
    "billed_amount": "amount", "payer_name": "payer", "admission_ward": "ward",
}


def humanise(field: str) -> str:
    return _FIELD_WORDS.get(field, field.replace("_", " "))


def known_field(name: str) -> bool:
    return any(name in catalogue for catalogue in FIELD_CATALOGUE.values())


# --------------------------------------------------------------------------- #
# The screen map
# --------------------------------------------------------------------------- #

Screen = Literal["list page", "record page"]


class ModuleView(BaseModel):
    """One module as the agent sees it: content, labels and buttons."""

    title: str
    path: str
    layer: HISLayer
    confidence: float = 0.0
    list_fields: list[str]
    record_fields: list[str]
    labels: dict[str, str] = Field(default_factory=dict)          # field -> header as shown
    list_actions: dict[str, str] = Field(default_factory=dict)    # action id -> button label
    record_actions: dict[str, str] = Field(default_factory=dict)
    unknown_controls: list[tuple[Screen, str]] = Field(default_factory=list)
    unknown_headers: list[tuple[Screen, str]] = Field(default_factory=list)

    def fields(self) -> set[str]:
        return {*self.list_fields, *self.record_fields}

    def has_action(self, action: str) -> bool:
        return action in self.list_actions or action in self.record_actions

    def action_label(self, action: str) -> str:
        return self.list_actions.get(action) or self.record_actions[action]

    def screen_for_fields(self, fields: Iterable[str]) -> Screen:
        return "list page" if all(f in self.list_fields for f in fields) else "record page"

    def label(self, field: str) -> str:
        shown = self.labels.get(field, field)
        return humanise(field) if shown == field else shown


class Placement(BaseModel):
    """Where one step happens, in the HIS as last crawled -- or why it cannot be placed."""

    module: str
    path: str | None = None
    screen: Screen | None = None
    button: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    elsewhere: list[str] = Field(default_factory=list)            # "Payer is on Insurance & Payers, list page"
    withheld: str | None = None                                   # the reason, when it cannot be placed

    def where(self) -> str:
        parts = [self.module]
        if self.path:
            parts.append(self.path)
        if self.screen:
            parts.append(self.screen)
        return ", ".join(parts)


class ScreenMap:
    """The HIS as the agent will describe it. ``ScreenMap()`` is the map-less default."""

    def __init__(self, modules: list[ModuleView] | None = None, *, source: str = "",
                 discovered: str | None = None) -> None:
        self.modules = modules
        self.source = source
        self.discovered = discovered

    @property
    def crawled(self) -> bool:
        return self.modules is not None

    @classmethod
    def from_navigation(
        cls, nav: "NavigationMap", control_aliases: dict[str, str] | None = None,
    ) -> "ScreenMap":
        views: list[ModuleView] = []
        for m in nav.modules:
            if m.inferred_layer is None:
                continue
            view = ModuleView(
                title=m.title, path=m.list_path, layer=m.inferred_layer,
                confidence=m.layer_confidence,
                list_fields=list(m.columns), record_fields=list(m.detail_fields),
                labels=dict(m.labels),
            )
            for screen, controls, into in (("list page", m.list_controls, view.list_actions),
                                            ("record page", m.record_controls, view.record_actions)):
                for label in controls:
                    action = match_control(label, control_aliases)
                    if action is None:
                        view.unknown_controls.append((screen, label))
                    else:
                        into.setdefault(action, label)
            for screen, names in (("list page", m.columns), ("record page", m.detail_only())):
                view.unknown_headers += [(screen, n) for n in names if not known_field(n)]
            views.append(view)
        return cls(views, source=nav.base_url, discovered=nav.discovered_at.date().isoformat())

    # ------------------------------------------------------------------ lookup

    def in_layer(self, layer: HISLayer) -> list[ModuleView]:
        return [m for m in (self.modules or []) if m.layer == layer]

    def module_titled(self, title: str) -> ModuleView | None:
        return next((m for m in self.modules or [] if m.title == title), None)

    def place(self, layer: HISLayer, fields: list[str], action: str | None,
              previous: Placement | None = None, continues: bool = False) -> Placement:
        """Put one step on a page: a module, a screen, a button label, column labels.

        ``continues`` keeps the step where ``previous`` left off -- the form a
        button opened -- and only checks that its fields can be found.
        """

        if not self.crawled:
            return Placement(
                module=LAYER_NAMES[layer],
                button=f'"{ACTIONS[action].label}"' if action else None,
                labels={f: humanise(f) for f in fields},
            )

        modules = self.in_layer(layer)
        here = self.module_titled(previous.module) if continues and previous is not None else None
        if continues and previous is not None and previous.withheld:
            return Placement(module=previous.module, withheld="the step before it could not be placed")
        if not modules and here is None:
            return Placement(module=LAYER_NAMES[layer],
                             withheld=f"no module holding {LAYER_NAMES[layer]} data was found")

        missing = [f for f in fields
                   if not any(f in m.fields() for m in [*modules, *([here] if here else [])])]
        problems = []
        if missing:
            problems.append(", ".join(humanise(f) for f in missing)
                            + f" could not be found on any {LAYER_NAMES[layer]} page")

        if here is not None:
            if problems:
                return Placement(module=here.title, withheld="; ".join(problems))
            labels, elsewhere = self._labels(here, modules, fields)
            return Placement(module=here.title, path=here.path, screen=previous.screen,
                             labels=labels, elsewhere=elsewhere)

        candidates = modules
        if action:
            # The button decides the page. An update may move it to a module the
            # crawler files under another layer; follow it there.
            candidates = ([m for m in modules if m.has_action(action)]
                          or [m for m in self.modules or [] if m.has_action(action)])
            if not candidates:
                problems.insert(0, f'no button for "{ACTIONS[action].label}" was found on any '
                                   f'{LAYER_NAMES[layer]} page')
        if problems:
            return Placement(module=(candidates or modules)[0].title, withheld="; and ".join(problems))

        def score(m: ModuleView) -> tuple:
            held = sum(1 for f in fields if f in m.fields())
            return (held, previous is not None and previous.module == m.title, m.confidence)

        chosen = max(candidates, key=score)

        # The screen: where the button is, else where the fields are, else where we were.
        shown = [f for f in fields if f in chosen.fields()]
        if action:
            same_record = (previous is not None and previous.module == chosen.title
                           and previous.screen == "record page")
            if action in chosen.record_actions and (same_record or action not in chosen.list_actions):
                screen: Screen | None = "record page"
            else:
                screen = "list page"
        elif shown:
            screen = chosen.screen_for_fields(shown)
        else:
            screen = previous.screen if previous is not None and previous.module == chosen.title else None

        labels, elsewhere = self._labels(chosen, modules, fields)
        return Placement(
            module=chosen.title, path=chosen.path, screen=screen,
            button=f'"{chosen.action_label(action)}"' if action else None,
            labels=labels, elsewhere=elsewhere,
        )

    @staticmethod
    def _labels(chosen: ModuleView, modules: list[ModuleView],
                fields: list[str]) -> tuple[dict[str, str], list[str]]:
        """Each field's on-screen label, and a pointer for any held by another module."""

        labels: dict[str, str] = {}
        elsewhere: list[str] = []
        for f in fields:
            if f in chosen.fields():
                labels[f] = chosen.label(f)
                continue
            other = max((m for m in modules if f in m.fields()), key=lambda m: m.confidence)
            labels[f] = other.label(f)
            elsewhere.append(f"{labels[f]} is on {other.title}, {other.screen_for_fields([f])}")
        return labels, elsewhere


__all__ = [
    "Action", "ACTIONS", "normalise", "match_control", "LAYER_NAMES", "humanise", "known_field",
    "ModuleView", "Placement", "ScreenMap",
]
