"""Sticky conversation state (PRD 5.1), shown to the user as chips. Kept apart from session.py so the turn
logic stays readable; session.py re-exports it."""
from dataclasses import dataclass, field


@dataclass
class SessionState:
    """What one conversation remembers between turns."""
    active_task: str | None = None  # 'search' | 'match' (what a new restriction re-runs)
    query_text: str | None = None
    query_any: list = field(default_factory=list)  # title keywords, any of (cuisine proxy)
    query_label: str | None = None  # how the UI names query_any ('gujarati (title keywords)')
    include: list = field(default_factory=list)
    exclude: list = field(default_factory=list)  # plain words, canonicalized at execution
    exclude_tags: list = field(default_factory=list)
    diets: list = field(default_factory=list)  # presets ('vegan') whose tags are all in exclude_tags
    max_steps: int | None = None
    have: list = field(default_factory=list)  # as typed, quantities included ("2 eggs")
    prefs: list = field(default_factory=list)  # use_most / fewest_extra / fewest_steps / no_staples
    limit: int | None = None
    strict_may_contain: bool = False
    last_results: list = field(default_factory=list)  # recipe ids in displayed order
    titles: dict = field(default_factory=dict)
    selected_recipe_id: str | None = None
    history: list = field(default_factory=list)  # (user text, first reply line), last 6
    kept_note: bool = False

    @property
    def last_titles(self) -> list[tuple[str, str]]:
        return [(i, self.titles.get(i, "")) for i in self.last_results]

    def chips(self) -> str:
        """One-line view of the state."""
        c = [f"task={self.active_task}"] if self.active_task else []
        c += [f"dish='{self.query_text or self.query_label}'"] if self.query_text or self.query_label else []
        c += [f"diet: {d}" for d in self.diets]
        c += [f"no {x}" for x in self.exclude_tags + self.exclude]
        c += [f"max {self.max_steps} steps"] if self.max_steps is not None else []
        c += [f"have: {', '.join(self.have)}"] if self.have else []
        c += [f"prefs: {', '.join(self.prefs)}"] if self.prefs else []
        c += [f"selected: {self.selected_recipe_id}"] if self.selected_recipe_id else []
        return " · ".join(c) or "(empty)"
