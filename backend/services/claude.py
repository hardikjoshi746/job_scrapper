import os
import anthropic

client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip())

async def tailor_resume(resume_text: str, job_description: str, template_html: str) -> str:
    message = await client.messages.create(
        model="claude-sonnet-5",
        max_tokens=8000,
        messages=[
            {
                "role": "user",
                "content": f"""You are an ATS resume expert. Your job is to produce a complete, filled-in resume HTML by replacing ALL placeholder text in the template with REAL content from the candidate's resume, tailored to the job description.

IMPORTANT: The template contains placeholder text like "Full Name", "Job Title", "Company Name", "City, ST", "Bullet point describing...", "Skill", "University Name" etc. You MUST replace ALL of these with the candidate's actual information. Do not leave any placeholder text in the output.

LOCATION: If the job description specifies a city/state/country, update the candidate's location in the header to match that location. If the job is remote, keep the candidate's original location.

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

8. ALL SECTIONS ARE MANDATORY. You MUST include every section from the template: Professional
   Summary, Professional Experience, Academic Projects, Achievements, Technical Skills,
   Certifications, AND Education. Never omit any section.

9. PROFESSIONAL SUMMARY. Write 2-3 sentences in the summary section that pack in the most
   important keywords from the job description while honestly reflecting the candidate's background.
   This is the highest-value ATS section — make every word count.

10. ONE PAGE, NO GAPS. The resume must fill the entire A4 page with no large empty spaces at
    the bottom. If content is too short, expand bullet points to 2 lines, add a relevant extra
    bullet per role, or expand the summary. If too long, trim bullets to 1 line. The page should
    look completely full with zero wasted whitespace.

11. BOLD FOR IMPACT. In every bullet point, bold TWO types of phrases using <strong> tags:
    (a) The opening action + result: bold the first clause that states what was achieved and
        the metric, e.g. "<strong>Slashed AI agent token consumption by 4x</strong> by implementing..."
        or "<strong>Reduced error rates by 40%</strong> through...". This is the most important
        part of each bullet — make it pop.
    (b) Key technologies and JD keywords inline: bold specific tools, frameworks, or exact
        phrases from the job description that appear later in the sentence,
        e.g. "by implementing <strong>RAG pipelines</strong> and <strong>vector database</strong> retrieval".
    Do NOT bold filler words, prepositions, or entire sentences. Each bullet should have
    1-2 bold phrases maximum. The result: scannable bullets where the achievement and
    key tech both stand out at a glance.

Output:
Return ONLY the complete HTML, no explanation, no markdown code blocks, no commentary before or
after the HTML."""
            }
        ]
    )
    # find the first text block (Claude may include ThinkingBlocks before the actual response)
    for block in message.content:
        if block.type == "text":
            return block.text
    raise ValueError("No text block found in Claude response")