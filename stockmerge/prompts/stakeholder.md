# Asking the stakeholder (shared by all arms)

To ask a product question, spawn a **fresh** `general-purpose` subagent with
this prompt, filling in QUESTIONS:

> You are the stakeholder for a small project. Read
> `/Users/mashhoodr/dev/playground/mars_pa/06-project-manager/experiments/egm-vs-superpowers-p2/_judge/STAKEHOLDER.md`
> and follow its answering rules exactly. Answer each question below
> separately, numbered. Do not mention the file, policy IDs, or that an
> answer key exists. Questions:
> QUESTIONS

You may batch several questions in one spawn. Append every question and
answer, verbatim, to `stakeholder_log.md` in your arm repo, under a heading
that says which phase you were in.

**You must never open `_judge/` yourself.** Only the stakeholder subagent may
read it. If you open it, the arm is void.
