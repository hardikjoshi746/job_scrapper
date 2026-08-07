import anthropic 
from config import settings

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

async def tailor_resume(resume_text: str, job_description: str, template_html: str) -> str:
    message = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""You are an ATS resume expert. Your job is to tailor the candidate's real
resume to the job description as aggressively as possible WITHOUT inventing experience that
isn't there.

<template>
{template_html}
</template>

<resume>
{resume_text}
</resume>

<job_description>
{job_description}
</job_description>

How to tailor:

1. READ THE JD FOR EXACT KEYWORDS AND PHRASING. Wherever the candidate's real experience
   genuinely matches a requirement, rewrite that bullet to use the JD's own terminology
   (e.g. if the JD says "distributed systems" and the resume says "backend services across
   multiple servers," rephrase using "distributed systems"). Reuse the JD's language wherever
   it's an honest description of what the candidate did.

2. REORDER, DON'T INVENT. Reorder bullets and skills so the most JD-relevant ones lead. Pull
   the candidate's strongest real matches to the top of each section and the skills list.

3. ADJACENT-SKILL FRAMING IS OK, NEW SKILLS ARE NOT. You may describe a real skill using a
   closely related term the JD uses (e.g. candidate used Redux -> may mention "Redux Toolkit"
   only if this is a fair characterization; general REST API work -> may use "web services"
   language the JD prefers) as long as the underlying work is genuinely the same activity.
   You may NOT add a tool, language, framework, certification, or years of experience that
   does not appear anywhere in the source resume. If the JD asks for something the resume has
   zero basis for (e.g. a named framework, a specific cloud service, a required certification),
   leave it out rather than fabricate it.

4. NO INVENTED METRICS. Never create a number, percentage, or scale claim that isn't in the
   source resume. You may rephrase an existing metric's framing but not its value.

5. PRESERVE STRUCTURE. Keep the exact HTML structure and CSS from the template. Keep the same
   number of bullets per role as the source resume unless a role has zero relevant content, in
   which case trim rather than pad with fabricated bullets.

6. ONE-PAGE DISCIPLINE. Keep total content sized for a single page at the template's font
   sizes. If content is too long, cut the least JD-relevant bullets rather than shrinking fonts
   below what the template defines.

7. HONESTY OVER KEYWORD-STUFFING. If the resume is a poor match for this JD in a core, required
   area, do not force a match — better to under-optimize than to produce a resume that collapses
   under a technical follow-up question. This tool answers to the candidate, not the ATS.

Output:
Return ONLY the complete HTML, no explanation, no markdown code blocks, no commentary before or
after the HTML."""
            }
        ]
    )
    return message.content[0].text