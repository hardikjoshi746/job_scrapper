"""
Universal ATS autofiller.

Design: the GENERIC resolver is the main path. Per-ATS adapters are thin
overrides that only patch what the generic layer gets wrong. Adding a new
job portal should usually require zero code.

    harvest (all frames) -> classify -> match -> fill -> report unfilled

Requires: playwright
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from playwright.async_api import Frame, Page

# --------------------------------------------------------------------------
# 1. Canonical field taxonomy
# --------------------------------------------------------------------------
# Order matters: first match wins, so put specific patterns above generic ones.
# Patterns are matched against normalized label context (lowercased, collapsed).

FIELD_PATTERNS: list[tuple[str, list[str]]] = [
    # --- name -------------------------------------------------------------
    ("first_name",      [r"\bfirst\s*name\b", r"\bgiven\s*name\b", r"\bforename\b", r"^fname$"]),
    ("last_name",       [r"\blast\s*name\b", r"\bfamily\s*name\b", r"\bsurname\b", r"^lname$"]),
    ("middle_name",     [r"\bmiddle\s*(name|initial)\b"]),
    ("preferred_name",  [r"\bpreferred\s*(first\s*)?name\b", r"\bnickname\b"]),
    ("full_name",       [r"\b(full|legal|your)\s*name\b", r"^name$"]),
    # --- contact ----------------------------------------------------------
    ("email",           [r"\be-?mail\b"]),
    ("phone",           [r"\bphone\b", r"\bmobile\b", r"\btelephone\b", r"\bcell\b"]),
    ("phone_country",   [r"\b(country\s*(code|phone)|phone\s*(device\s*)?type)\b"]),
    # --- location ---------------------------------------------------------
    ("address_line1",   [r"\baddress\s*(line\s*)?1\b", r"\bstreet\s*address\b", r"^address$"]),
    ("address_line2",   [r"\baddress\s*(line\s*)?2\b", r"\b(apt|suite|unit)\b"]),
    ("city",            [r"\bcity\b", r"\btown\b", r"\blocality\b"]),
    ("state",           [r"\bstate\b", r"\bprovince\b", r"\bregion\b", r"\bcounty\b"]),
    ("postal_code",     [r"\b(zip|postal)\s*code\b", r"^zip$", r"\bpostcode\b"]),
    ("country",         [r"\bcountry\b(?!\s*code)"]),
    ("location",        [r"\b(current\s*)?location\b", r"\bwhere.*(based|located)\b"]),
    # --- links ------------------------------------------------------------
    ("linkedin",        [r"\blinked\s*-?in\b"]),
    ("github",          [r"\bgit\s*hub\b"]),
    ("portfolio",       [r"\bportfolio\b", r"\bpersonal\s*(web)?site\b", r"\bwebsite\b"]),
    ("twitter",         [r"\btwitter\b", r"\bx\.com\b"]),
    ("other_url",       [r"\bother\s*(website|url|link)\b"]),
    # --- documents --------------------------------------------------------
    ("resume",          [r"\bresum[eé]\b", r"\bcv\b", r"\bupload.*(resume|cv)\b"]),
    ("cover_letter",    [r"\bcover\s*letter\b"]),
    # --- employment -------------------------------------------------------
    ("current_company", [r"\bcurrent\s*(company|employer)\b", r"\bcompany\b(?!.*previous)"]),
    ("current_title",   [r"\b(current\s*)?(job\s*)?title\b", r"\bposition\b(?!.*applied)"]),
    ("years_experience",[r"\byears?\s*(of\s*)?(relevant\s*)?experience\b"]),
    ("school",          [r"\bschool\b", r"\buniversity\b", r"\bcollege\b", r"\binstitution\b"]),
    ("degree",          [r"\bdegree\b", r"\bqualification\b"]),
    ("discipline",      [r"\b(discipline|major|field\s*of\s*study)\b"]),
    ("grad_year",       [r"\b(graduation|end)\s*(year|date)\b"]),
    # --- logistics (fill only if the user set an explicit answer) ---------
    ("work_authorized", [r"\b(legally\s*)?authoriz(ed|ation)\s*to\s*work\b",
                         r"\bright\s*to\s*work\b", r"\beligible\s*to\s*work\b"]),
    ("needs_sponsorship",[r"\bsponsorship\b", r"\bvisa\s*(support|status)\b",
                          r"\brequire.*(h-?1b|sponsor)\b"]),
    ("notice_period",   [r"\bnotice\s*period\b", r"\bavailable\s*to\s*start\b", r"\bstart\s*date\b"]),
    ("salary_expectation",[r"\b(salary|compensation)\s*(expectation|requirement|range)\b",
                           r"\bexpected\s*(salary|pay|ctc)\b", r"\bdesired\s*salary\b"]),
    ("relocate",        [r"\bwilling\s*to\s*relocate\b", r"\brelocation\b"]),
    ("remote_pref",     [r"\bremote\b", r"\bhybrid\b", r"\bwork\s*preference\b"]),
    ("how_heard",       [r"\bhow\s*did\s*you\s*hear\b", r"\bsource\b", r"\breferr?(al|ed\s*by)\b"]),
    # --- demographics (classified so we can deliberately SKIP them) -------
    ("eeo_gender",      [r"\bgender\b", r"\bsex\b"]),
    ("eeo_race",        [r"\b(race|ethnicity|hispanic|latino)\b"]),
    ("eeo_veteran",     [r"\bveteran\b", r"\bmilitary\s*service\b"]),
    ("eeo_disability",  [r"\bdisabilit(y|ies)\b", r"\bsection\s*503\b"]),
    ("eeo_pronouns",    [r"\bpronouns?\b"]),
    ("birth_date",      [r"\b(date\s*of\s*birth|birth\s*date|dob)\b", r"\bage\b"]),
    ("ssn",             [r"\b(ssn|social\s*security)\b", r"\bnational\s*id\b"]),
    ("criminal_history",[r"\b(convict|felony|criminal|background\s*check)\b"]),
]

COMPILED = [(k, [re.compile(p) for p in pats]) for k, pats in FIELD_PATTERNS]

# Never auto-fill these, even if the profile has a value. Legal risk, or the
# answer is protected info the user must volunteer themselves.
NEVER_AUTOFILL = {
    "eeo_gender", "eeo_race", "eeo_veteran", "eeo_disability", "eeo_pronouns",
    "birth_date", "ssn", "criminal_history",
}

# Fill only when the profile has an explicit, non-empty answer — never guess.
REQUIRES_EXPLICIT = {
    "needs_sponsorship", "work_authorized", "salary_expectation",
    "notice_period", "criminal_history",
}


# --------------------------------------------------------------------------
# 2. Profile
# --------------------------------------------------------------------------

@dataclass
class Profile:
    values: dict[str, Any] = field(default_factory=dict)
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    # Free-text answers the user pre-wrote, keyed by a regex matched against
    # the question text, e.g. {r"why.*(interested|want).*(company|role)": "..."}
    essay_answers: dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> Any:
        v = self.values.get(key)
        return v if v not in (None, "") else None

    def derive(self) -> None:
        """Fill obvious composites so we don't need them in the taxonomy twice."""
        f, l = self.values.get("first_name"), self.values.get("last_name")
        if f and l:
            self.values.setdefault("full_name", f"{f} {l}")
        if self.values.get("city") and self.values.get("state"):
            self.values.setdefault(
                "location", f"{self.values['city']}, {self.values['state']}"
            )


# --------------------------------------------------------------------------
# 3. Harvest — one round trip per frame, returns every visible control
#    plus everything that could possibly be its label.
# --------------------------------------------------------------------------

HARVEST_JS = r"""
() => {
  const SEL = [
    'input:not([type=hidden]):not([type=submit]):not([type=button])',
    'select', 'textarea',
    '[role=combobox]', '[role=listbox]', '[role=radiogroup]',
    '[contenteditable=true]'
  ].join(',');

  const visible = el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  const txt = n => (n && n.innerText ? n.innerText : '').replace(/\s+/g, ' ').trim();

  const out = [];
  let i = 0;
  for (const el of document.querySelectorAll(SEL)) {
    // file inputs are often visually hidden behind a styled button — keep them
    const isFile = el.type === 'file';
    if (!isFile && !visible(el)) continue;

    const afId = 'af-' + (i++);
    el.setAttribute('data-af-id', afId);

    const bits = [];
    if (el.id) {
      const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (l) bits.push(txt(l));
    }
    const wrap = el.closest('label');
    if (wrap) bits.push(txt(wrap));

    const lb = el.getAttribute('aria-labelledby') || el.getAttribute('aria-describedby');
    if (lb) for (const id of lb.split(/\s+/)) {
      const n = document.getElementById(id);
      if (n) bits.push(txt(n));
    }
    for (const a of ['aria-label','placeholder','name','id','title',
                     'data-automation-id','data-qa','data-testid','data-test']) {
      const v = el.getAttribute(a);
      if (v) bits.push(v);
    }
    const fs = el.closest('fieldset');
    if (fs) { const lg = fs.querySelector('legend'); if (lg) bits.push(txt(lg)); }

    // nearest ancestor that carries short text = the visual question
    let p = el.parentElement, hops = 0;
    while (p && hops++ < 5) {
      const t = txt(p);
      if (t && t.length < 300) { bits.push(t); break; }
      p = p.parentElement;
    }

    let options = null;
    if (el.tagName === 'SELECT') {
      options = [...el.options].map(o => ({ text: txt(o) || o.text, value: o.value }));
    }

    out.push({
      afId,
      tag: el.tagName.toLowerCase(),
      type: el.type || el.getAttribute('role') || null,
      required: el.required || el.getAttribute('aria-required') === 'true',
      value: (el.value || '').slice(0, 200),
      checked: !!el.checked,
      options,
      context: bits.join(' | ').slice(0, 600),
    });
  }
  return out;
}
"""


@dataclass
class Control:
    frame: Frame
    af_id: str
    tag: str
    type: Optional[str]
    required: bool
    value: str
    checked: bool
    options: Optional[list[dict]]
    context: str
    key: Optional[str] = None
    confidence: float = 0.0

    @property
    def locator(self):
        return self.frame.locator(f'[data-af-id="{self.af_id}"]')


async def harvest(page: Page) -> list[Control]:
    controls: list[Control] = []
    for frame in page.frames:  # ATSes embedded via iframe are the norm
        try:
            rows = await frame.evaluate(HARVEST_JS)
        except Exception:
            continue  # cross-origin or detached
        for r in rows:
            controls.append(Control(frame=frame, af_id=r["afId"], tag=r["tag"],
                                    type=r["type"], required=r["required"],
                                    value=r["value"], checked=r["checked"],
                                    options=r["options"], context=r["context"]))
    return controls


# --------------------------------------------------------------------------
# 4. Classify
# --------------------------------------------------------------------------

def normalize(s: str) -> str:
    s = s.lower().replace("_", " ").replace("-", " ")
    s = re.sub(r"[^a-z0-9\s|.]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def classify(ctx: str) -> tuple[Optional[str], float]:
    """Return (canonical_key, confidence 0..1)."""
    n = normalize(ctx)
    if not n:
        return None, 0.0
    for key, pats in COMPILED:
        for p in pats:
            m = p.search(n)
            if not m:
                continue
            # Earlier in the context blob == closer to an explicit label
            # (labels are pushed before generic ancestor text), so trust it more.
            pos = m.start() / max(len(n), 1)
            conf = 0.95 if pos < 0.35 else 0.75 if pos < 0.7 else 0.55
            return key, conf
    return None, 0.0


def classify_all(controls: list[Control]) -> None:
    for c in controls:
        c.key, c.confidence = classify(c.context)
        if c.type == "file" and c.key is None:
            c.key, c.confidence = "resume", 0.6  # lone file input ≈ resume


# --------------------------------------------------------------------------
# 5. Fill — one handler per widget kind, not per portal
# --------------------------------------------------------------------------

YES = re.compile(r"^\s*(yes|y|true|i am|i do)\b")
NO = re.compile(r"^\s*(no|n|false|i am not|i do not|i don'?t)\b")


def pick_option(options: list[dict], want: Any) -> Optional[str]:
    """Best-effort map a profile value onto a real <option>."""
    if want is None:
        return None
    w = normalize(str(want))
    if isinstance(want, bool):
        w = "yes" if want else "no"
    texts = [(o, normalize(o["text"])) for o in options if o["text"]]
    for o, t in texts:                       # exact
        if t == w:
            return o["value"]
    for o, t in texts:                       # yes/no semantics
        if w == "yes" and YES.match(t):
            return o["value"]
        if w == "no" and NO.match(t):
            return o["value"]
    for o, t in texts:                       # containment
        if t and (w in t or t in w):
            return o["value"]
    return None


async def fill_control(c: Control, profile: Profile) -> str:
    """Returns: 'filled' | 'skipped' | 'needs_user' | 'error'."""
    if c.key is None or c.confidence < 0.55:
        return "needs_user"
    if c.key in NEVER_AUTOFILL:
        return "skipped"

    # documents
    if c.type == "file":
        path = profile.resume_path if c.key == "resume" else profile.cover_letter_path
        if not path:
            return "needs_user"
        await c.locator.set_input_files(path)
        return "filled"

    val = profile.get(c.key)
    if val is None:
        if c.key in REQUIRES_EXPLICIT:
            return "needs_user"
        # try the user's pre-written essay answers for free-text questions
        if c.tag == "textarea":
            for pat, answer in profile.essay_answers.items():
                if re.search(pat, normalize(c.context)):
                    await c.locator.fill(answer)
                    return "filled"
        return "needs_user"

    try:
        if c.tag == "select":
            opt = pick_option(c.options or [], val)
            if not opt:
                return "needs_user"
            await c.locator.select_option(value=opt)
            return "filled"

        if c.type in ("checkbox", "radio"):
            want = str(val).lower() in ("yes", "true", "1")
            label = normalize(c.context)
            if (want and YES.match(label)) or (not want and NO.match(label)):
                await c.locator.check()
                return "filled"
            return "needs_user"

        if c.type in ("combobox", "listbox"):
            return await fill_typeahead(c, str(val))

        await c.locator.fill(str(val))
        return "filled"
    except Exception:
        return "error"


async def fill_typeahead(c: Control, val: str) -> str:
    """React-select / Workday-style: type, wait for listbox, click best match."""
    try:
        await c.locator.click()
        await c.locator.type(val, delay=40)
        opts = c.frame.locator('[role=option], li[id*=option], [class*=option]')
        await opts.first.wait_for(state="visible", timeout=2500)
        n = min(await opts.count(), 12)
        target, wnorm = None, normalize(val)
        for i in range(n):
            t = normalize(await opts.nth(i).inner_text())
            if t == wnorm:
                target = opts.nth(i)
                break
            if target is None and wnorm in t:
                target = opts.nth(i)
        (target or opts.first).click and await (target or opts.first).click()
        return "filled"
    except Exception:
        await c.frame.page.keyboard.press("Escape")
        return "needs_user"


# --------------------------------------------------------------------------
# 6. ATS fingerprinting — URL is a hint, DOM is the proof
# --------------------------------------------------------------------------

URL_SIGNS = {
    "greenhouse":     [r"greenhouse\.io", r"job-boards\.greenhouse"],
    "lever":          [r"lever\.co"],
    "ashby":          [r"ashbyhq\.com"],
    "workday":        [r"myworkdayjobs\.com", r"\.workday\.com"],
    "smartrecruiters":[r"smartrecruiters\.com"],
    "workable":       [r"workable\.com"],
    "icims":          [r"icims\.com"],
    "taleo":          [r"taleo\.net"],
    "jobvite":        [r"jobvite\.com"],
    "successfactors": [r"successfactors\.com", r"sapsf\.com"],
    "bamboohr":       [r"bamboohr\.com"],
    "recruitee":      [r"recruitee\.com"],
    "teamtailor":     [r"teamtailor\.com"],
    "breezy":         [r"breezy\.hr"],
    "rippling":       [r"rippling(-ats)?\.com"],
}

DOM_SIGNS = {
    "workday":    "[data-automation-id]",
    "greenhouse": "#grnhse_app, [id^=grnhse], form[action*=greenhouse]",
    "lever":      ".application-form, [class^=posting]",
    "ashby":      "[class*=ashby], [data-highlight]",
    "icims":      "#icims_content_iframe, .iCIMS_MainWrapper",
}


async def detect_ats(page: Page) -> str:
    urls = [page.url] + [f.url for f in page.frames]
    for name, pats in URL_SIGNS.items():
        if any(re.search(p, u or "") for p in pats for u in urls):
            return name
    for name, sel in DOM_SIGNS.items():
        for frame in page.frames:
            try:
                if await frame.locator(sel).count():
                    return name
            except Exception:
                pass
    return "generic"


# --------------------------------------------------------------------------
# 7. Adapters — only patch what the generic layer misses
# --------------------------------------------------------------------------

Adapter = dict[str, Any]
ADAPTERS: dict[str, Adapter] = {}


def adapter(name: str) -> Callable:
    def deco(fn):
        ADAPTERS[name] = fn()
        return fn
    return deco


@adapter("workday")
def _workday() -> Adapter:
    # Workday's data-automation-id values are stable across every tenant.
    # This is the single highest-value override you can write.
    return {
        "direct": {
            "legalNameSection_firstName": "first_name",
            "legalNameSection_lastName": "last_name",
            "addressSection_addressLine1": "address_line1",
            "addressSection_city": "city",
            "addressSection_postalCode": "postal_code",
            "addressSection_countryRegion": "state",
            "email": "email",
            "phone-number": "phone",
            "phone-device-type": "phone_country",
            "resumeUpload": "resume",
        },
        "attr": "data-automation-id",
        # Workday is a multi-step wizard behind an account wall.
        "next_selector": '[data-automation-id="bottom-navigation-next-button"]',
        "max_steps": 6,
    }


@adapter("greenhouse")
def _greenhouse() -> Adapter:
    return {
        "direct": {"first_name": "first_name", "last_name": "last_name",
                   "email": "email", "phone": "phone", "resume": "resume"},
        "attr": "name",
    }


def apply_adapter(controls: list[Control], ats: str) -> None:
    ad = ADAPTERS.get(ats)
    if not ad:
        return
    attr, direct = ad["attr"], ad["direct"]
    for c in controls:
        for token, key in direct.items():
            # the attribute value is already inside the harvested context blob
            if re.search(rf"(^|\|\s*){re.escape(token)}(\s*\||$)", c.context, re.I):
                c.key, c.confidence = key, 1.0
                break


# --------------------------------------------------------------------------
# 8. Orchestrator
# --------------------------------------------------------------------------

@dataclass
class Report:
    ats: str
    filled: list[tuple[str, str]] = field(default_factory=list)      # (key, context)
    needs_user: list[tuple[str, str, bool]] = field(default_factory=list)  # (af_id, ctx, required)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> list[tuple[str, str, bool]]:
        return [x for x in self.needs_user if x[2]]


async def autofill(page: Page, profile: Profile, *, submit: bool = False) -> Report:
    profile.derive()
    ats = await detect_ats(page)
    rep = Report(ats=ats)

    controls = await harvest(page)
    classify_all(controls)
    apply_adapter(controls, ats)

    for c in controls:
        if c.value or c.checked:
            continue  # already populated (resume parser, saved profile) — don't clobber
        status = await fill_control(c, profile)
        label = (c.context.split("|")[0] or c.context)[:80]
        if status == "filled":
            rep.filled.append((c.key or "?", label))
        elif status == "needs_user":
            rep.needs_user.append((c.af_id, label, c.required))
        elif status == "skipped":
            rep.skipped.append(label)
        else:
            rep.errors.append(label)
        await asyncio.sleep(0.08)  # let SPA validation settle

    # Never submit while required fields are unanswered, and never submit at all
    # unless the caller explicitly opted in.
    if submit and not rep.blocking:
        pass  # wire your own submit here, ideally behind a human confirmation

    return rep


async def autofill_wizard(page: Page, profile: Profile, max_steps: int = 6) -> list[Report]:
    """For multi-page flows (Workday, iCIMS, Taleo)."""
    ats = await detect_ats(page)
    nxt = ADAPTERS.get(ats, {}).get("next_selector")
    reports = []
    for _ in range(max_steps):
        reports.append(await autofill(page, profile))
        if reports[-1].blocking or not nxt:
            break
        btn = page.locator(nxt)
        if not await btn.count():
            break
        await btn.first.click()
        await page.wait_for_load_state("networkidle")
    return reports