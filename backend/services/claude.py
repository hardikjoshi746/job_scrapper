import os
import json
import anthropic
from openai import AsyncOpenAI

claude = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip())
openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", "").strip())

RESUME_CSS = """
@page { size: A4; margin: 20px 32px; }
* { box-sizing: border-box; }
body {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  color: #1a1a1a; max-width: 700px; margin: 0 auto;
  padding: 20px 32px; font-size: 8.2pt; line-height: 1.25;
}
:root { --accent: #0d2b6e; --dark: #1a1a1a; --mid: #444444; --light: #666666; }
.name { text-align: center; font-size: 22pt; font-weight: 700; color: var(--accent); margin: 0 0 4px 0; }
.contact { text-align: center; font-size: 8.4pt; color: var(--light); margin: 0 0 10px 0; }
.contact span::after { content: "  |  "; color: var(--light); }
.contact span:last-child::after { content: ""; }
h2.section {
  font-size: 9.5pt; font-weight: 700; color: var(--accent);
  text-transform: uppercase; letter-spacing: 0.3px;
  margin: 8px 0 3px 0; padding-bottom: 2px;
  border-bottom: 0.8pt solid var(--accent);
}
.entry-header { display: flex; justify-content: space-between; align-items: baseline; margin-top: 5px; }
.entry-title-line { font-size: 8.8pt; }
.entry-title { font-weight: 700; color: var(--dark); }
.entry-company { color: var(--light); font-weight: 400; }
.entry-dates { font-size: 8.8pt; color: var(--mid); white-space: nowrap; }
ul.bullets { list-style: none; margin: 3px 0 0 0; padding: 0; }
ul.bullets li { position: relative; padding-left: 14px; margin-bottom: 2px; font-size: 8.6pt; color: var(--dark); }
ul.bullets li::before {
  content: ""; position: absolute; left: 2px; top: 5px;
  width: 4px; height: 4px; border-radius: 50%; background: var(--accent);
}
.summary { font-size: 8.6pt; color: var(--mid); margin: 4px 0 0 0; line-height: 1.4; }
.skill-row { font-size: 8.6pt; margin-bottom: 3px; }
.skill-label { font-weight: 700; color: var(--dark); }
.skill-values { color: var(--mid); }
.edu-entry { font-size: 8.8pt; margin-bottom: 2px; }
.edu-school { font-weight: 700; color: var(--dark); }
.edu-degree { color: var(--light); }
@media print { body { padding: 0; } }
"""


async def _generate_resume(
    resume_text: str,
    job_description: str,
    custom_instructions: str = "",
    feedback_context: str = "",
) -> str:
    """Generate a single tailored resume HTML. Returns complete HTML string."""
    custom_block = f"\n\nUSER INSTRUCTIONS:\n{custom_instructions}" if custom_instructions.strip() else ""
    feedback_block = feedback_context  # already formatted by caller

    prompt = f"""You are an ATS resume expert. Produce a complete, tailored HTML resume using the candidate's ACTUAL resume content below.

CRITICAL RULES — violating any is a failure:
1. KEEP EVERY JOB. Include ALL work experience entries from the source resume. Never drop, merge, or skip any job entry regardless of relevance.
2. USE ACTUAL CONTENT. Every name, title, company, date, degree, project, and achievement must come from the source resume. Never invent or omit data.
3. ONE PAGE. The entire resume must fit on one A4 page. Max 3 bullets per job, max 2 projects (2 bullets each), max 4 achievements. Cut least-relevant bullets if needed — never cut entire jobs.
4. TAILOR BULLETS. Rewrite bullets using the JD's exact keywords where the candidate's real experience matches. Use the JD's terminology but never fabricate skills or metrics.
5. BOLD FOR IMPACT. In each bullet, bold (a) the opening achievement + metric clause e.g. <strong>Reduced latency by 40%</strong> and (b) 1-2 specific JD keywords inline e.g. <strong>RAG pipelines</strong>. Max 2 bold phrases per bullet.
6. PROFESSIONAL SUMMARY. Write 2-3 sentences packing JD keywords while honestly reflecting the candidate's background.
7. SECTIONS. Include all sections present in the source resume. Only omit a section if the user instructions say to skip it.{custom_block}{feedback_block}

CSS TO USE:
<style>{RESUME_CSS}</style>

AVAILABLE CSS CLASSES:
- .name — candidate's full name (h1 or div)
- .contact with <span> children — contact info separated by |
- h2.section — section headings (Professional Summary, Professional Experience, etc.)
- .summary — paragraph under Professional Summary
- .entry-header > .entry-title-line (.entry-title + .entry-company) + .entry-dates — job/project header
- ul.bullets > li — bullet points
- .skill-row > .skill-label + .skill-values — skill category rows
- .edu-entry > .edu-school + .edu-degree — education entries

OUTPUT: Return ONLY a complete HTML document (<!doctype html> through </html>). No markdown, no code fences, no commentary.

<resume>
{resume_text}
</resume>

<job_description>
{job_description}
</job_description>"""

    message = await claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    for block in message.content:
        if block.type == "text":
            return block.text
    raise ValueError("No text block in Claude response")


async def _evaluate_ats(resume_html: str, job_description: str) -> dict:
    """Score resume against JD using OpenAI. Returns {score, matched_keywords, missing_keywords, suggestions}."""
    response = await openai_client.chat.completions.create(
        model="gpt-5.5",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict ATS (Applicant Tracking System) evaluator. "
                    "Return only a JSON object with these keys: "
                    "\"score\" (integer 0-100, keyword match percentage — be strict), "
                    "\"matched_keywords\" (array of important JD keywords/phrases found in resume), "
                    "\"missing_keywords\" (array of important JD keywords/phrases NOT in resume), "
                    "\"suggestions\" (array of up to 5 specific improvements to raise the score)."
                ),
            },
            {
                "role": "user",
                "content": f"<resume>\n{resume_html}\n</resume>\n\n<job_description>\n{job_description}\n</job_description>",
            },
        ],
        max_completion_tokens=1000,
    )
    text = response.choices[0].message.content.strip()
    return json.loads(text)


async def tailor_resume(
    resume_text: str,
    job_description: str,
    custom_instructions: str = "",
    max_iterations: int = 3,
) -> dict:
    """
    Agentic resume tailoring loop.
    Generates a resume, evaluates ATS score, and regenerates if score < 95.
    Returns: {html, ats_score, matched_keywords, missing_keywords, iterations}
    """
    feedback_context = ""
    html = None
    evaluation = {"score": 0, "matched_keywords": [], "missing_keywords": [], "suggestions": []}

    for iteration in range(1, max_iterations + 1):
        html = await _generate_resume(resume_text, job_description, custom_instructions, feedback_context)
        evaluation = await _evaluate_ats(html, job_description)

        score = evaluation.get("score", 0)

        if score >= 95:
            break

        # Build feedback context for next iteration
        if iteration < max_iterations:
            missing = ", ".join(evaluation.get("missing_keywords", []))
            suggestions = "\n- ".join(evaluation.get("suggestions", []))
            feedback_context = (
                f"\n\nPREVIOUS ATTEMPT ATS SCORE: {score}% — BELOW TARGET OF 95%.\n"
                f"MISSING KEYWORDS (must incorporate): {missing}\n"
                f"SPECIFIC IMPROVEMENTS REQUIRED:\n- {suggestions}\n"
                f"Fix all of the above in this new attempt while keeping all rules."
            )

    return {
        "html": html,
        "ats_score": evaluation.get("score", 0),
        "matched_keywords": evaluation.get("matched_keywords", []),
        "missing_keywords": evaluation.get("missing_keywords", []),
        "iterations": iteration,
    }
