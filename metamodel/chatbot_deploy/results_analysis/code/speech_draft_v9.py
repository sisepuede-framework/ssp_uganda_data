"""Draft speech for the DMDU 2026 talk, slide by slide, for deck v9.

Writes docs/DMDU_2026_speech_draft_v9.docx. "[c]" in the text marks a click,
placed to match the click builds in DMDU_2026_Talk_draft_models_1104_video_v9.pptx.
Refuses to overwrite, so Alexa's edits to the docx are never lost.
"""
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Cm

OUT = Path(__file__).resolve().parents[2] / "docs" / "DMDU_2026_speech_draft_v9.docx"
WPM = 130  # comfortable speaking pace for a conference talk
BLUE = RGBColor(0x1F, 0x4E, 0x9C)
GREY = RGBColor(0x6B, 0x70, 0x7B)
FONT = "Times New Roman"

# (slide, title, [paragraphs], q&a or None). "[c]" = click.
S = [
 (1, "Cover", [
  "Hello everyone. I'm [name], from [affiliation]. Today I'll talk about how we combined a surrogate model "
  "with an AI agent, and what we learned about the information we give that agent."], None),
 (2, "Divider: Context", ["Let me start with some context."], None),
 (3, "Engaging with a model no longer requires technical expertise", [
  "What you're seeing is an earlier version of what we built. A user asks in plain language for a policy "
  "outside the official NDC pathways, and quickly gets emissions, costs and benefits.",
  "It works, it looks great, and it would be easy to put it in front of a decision maker. But before doing "
  "that, we took a step back to understand how the components we were putting together actually behave."],
  "The video is a real answer from the earlier app; only the waiting time is cut. Don't quote its numbers as results."),
 (4, "A lot of potential, but significant risks", [
  "Because there is a lot of potential here, but also significant risks. [c] So our question was: "
  "is the tool engaging with the model as we expect?"], None),
 (5, "First, a surrogate model makes policy exploration fast", [
  "First, what makes this possible is a surrogate model. [c] SISEPUEDE, the full model, takes about three "
  "minutes per run, too slow for a conversation. [c] So we ran it in "
  "advance: 100,000 runs, covering many policies and many futures. [c] Then we trained an XGBoost surrogate on "
  "those runs, so we get answers without running the full model each time. [c] On runs it never saw, the "
  "median R² is 0.99. Today we only need it as the engine behind the agent."],
  "67 inputs, 258 outputs (emissions, costs, benefits, GDP), 2025–2070. 79,670 runs to train, 19,918 to test."),
 (6, "Every lever speaks its own units, so we use one scale", [
  "[c] Every lever speaks its own units: landfill gas recovered in percent, cereal yield in tonnes per "
  "hectare, bike efficiency in kilometres per kilowatt-hour. [c] So we put every lever on one common scale, a lever level from 0 to 1. "
  "Zero is business as usual, and one is the maximum of the range we explored. [c] And one lever can move many "
  "inputs at once, up to 186. One scale lets us treat every lever the same way."], None),
 (7, "Latin hypercube tests every part of every lever's range", [
  "With that scale, we sample with a Latin hypercube. [c] We cut each lever's range into equal slices. "
  "[c] We make sure every slice of every range is tried, so nothing is left out. [c] And we mix the levers at "
  "random, so each run is a new combination. [c] 54 levers and 13 uncertainties, about 100,000 runs: "
  "every part of every range, without trying every combination."],
  None),
 (8, "To answer a real question, we translate back", [
  "But the surrogate only understands lever levels, and people ask in real terms. So we translate back. [c] Take the lever level at 0, 0.5 and 1. [c] For landfill gas, that "
  "is 7, 31 and 55 percent. [c] For rural wastewater in septic tanks, 18, 40 and 63. [c] For electric cars and "
  "vans, 50, 61 and 72.",
  "[c] Each lever has its own straight line, so the same move, from 0 to 0.5, is 24 points on landfill gas "
  "but only 11 on electric cars. [c] That is the "
  "implication for the agent: it has to translate both ways, from words to lever levels and back, to get the "
  "size of a change right."], None),
 (9, "How can AI make computational experiments interactive?", [
  "So this is the problem. [c] RDM needs many slow runs, and technical expertise to run the model and the "
  "analysis. [c] Surrogates make runs fast, and AI as an intermediary makes that expertise accessible. [c] Our "
  "focus is what connects them: how rules and information govern the agent's behavior when it communicates "
  "model results."], None),
 (10, "Our questions: how to build it, what the agent must know", [
  "That gives us two research questions. [c] The first one is about building the system: how do we integrate "
  "the surrogate with an AI agent so non-technical users can go through the three components of RDM, and how "
  "do we evaluate it? [c] The second one is about information: what "
  "changes in the agent's behavior when we give it only how the variables are related, or also their values?"],
  None),
 (11, "Divider: Method", ["Let me show you how we built it."], None),
 (12, "The pipeline depends on rules and the agent's harness", [
  "[c] The policy maker asks a question in plain language. [c] The agent is the brain. Its capacities depend "
  "on the model we choose. [c] How the brain and the tools interact "
  "depends on the harness we build for it. [c] But a brain that only thinks and answers "
  "back is not enough. It needs tools to execute processes: six tools that run deterministic methods. [c] And the tools have access to the surrogate we built and to the data we decide "
  "to provide."], None),
 (13, "The harness sets how the agent and the tools interact", [
  "The harness does four things. [c] State: it remembers. Each set of results gets an id that the next tool can use. [c] Rules: what it won't allow. It rejects a lever outside its range, and the failure "
  "threshold must come from the user, not from the agent. [c] Log: it records every tool call, every reply, and a summary of the agent's thinking, "
  "which is what lets us evaluate it. [c] Limits: how far the agent can go, at most 20 requests to "
  "the model per conversation. [c] And there is no script of steps: the agent chooses which tools to use, and in what order."],
  "A rule break returns an error and the agent can try again. Limits are the same in both versions; no "
  "conversation reached them (at most 16 requests, median 4). The thinking summary is stored, never scored."),
 (14, "Each tool has one job", [
  "These are the capabilities we give the agent. [c] The first two provide information. model_network tells it "
  "what a lever does and what moves a result. country_context describes Uganda as the model sees it. [c] The "
  "other four execute actions and follow RDM: run a policy across 500 futures, ask the user what counts as "
  "failure, find the conditions where it fails, and compare policies without naming a winner."], None),
 (15, "The tools alone didn't let the agent understand the system", [
  "And here is the real process. From the beginning I noticed that the tools weren't giving the agent "
  "enough data to understand the system. [c] It could see the levers going in "
  "and the results coming out. [c] But what does a lever mean? What happens in between? [c] The agent could run "
  "the surrogate, but it could not see inside it."], None),
 (16, "What data, and how? Not too little, not all of it", [
  "So we had a dilemma. [c] With too little information, the agent guesses what the levers mean. [c] If we give "
  "it all 100,000 runs, it becomes slow and costly. [c] What we wanted was just enough: what the agent needs, "
  "when it asks for it. [c] So how we give the data, and which data, became a design question, without losing "
  "our objective of evaluating how the agent behaves."],
  "'Slow and costly' is our design reasoning. We did not test giving the agent all the data."),
 (17, "The AI built Map, a knowledge graph, from the model's code", [
  "Our answer was a network for the model_network tool, built by the AI from the SISEPUEDE code. It has two "
  "versions. The first one we call Map, and it only has the relations between variables. [c] From the levers "
  "and uncertainties, to the input variables each lever changes, to the in-between variables the model "
  "computes, to the emissions in detail, and to the sector emissions the XGBoost predicts.",
  "[c] So the two ends match the XGBoost, and Map shows the agent what happens in between. "],
  "How do we know it's right? 93.9% of the 4,568 links seen in the runs have a path in the network "
  "(levers to emissions 97.8%). 804 nodes, 4,379 links. A link means 'used to compute', not causality."),
 (18, "Map+ adds the density of each variable from the runs", [
  "The second version is Map+. [c] It has the same links, but each node also includes the density of each "
  "variable, [c] from the 100,000 runs, [c] by lever level and by uncertainty level. [c] So it's a summary of the "
  "runs, not the whole dataset."],
  "Precisely: median and p10–p90, by lever third and uncertainty third, computed on a random sample of 4,989 "
  "runs. Checked against all the runs: the medians match closely; only very small lever effects are noisy."),
 (19, "Map and Map+ see different information on the same walk", [
  "This is one path through the network from the last two slides: the fuel shift in cars and vans. [c] With "
  "Map, the agent only sees names and units, from the lever down to the transport sector. [c] With Map+, it sees the same, plus the values. From lever low to lever high, the electric share "
  "goes from 50 to 72 percent, diesel kilometres from 5.3 to 3.7 billion, and transport CO₂ from 2.7 to 1.9 "
  "megatonnes. [c] And this is how we give it: one node at a time, so the agent takes only what it asks for."],
  "Values are 2050. Shares: the input at each end of the lever. The rest: median of the runs in the lever's "
  "lowest and highest third, with everything else varying."),
 (20, "Divider: Experiment", ["So how did we test it?"], None),
 (21, "Only one thing changes: the version of the network", [
  "[c] We keep everything the same: the prompt, the six tools, the agent model, the questions and the futures. "
  "[c] The only thing that changes is the version of the network the agent can see: Map, with the relations, "
  "or Map+, with the relations and the densities. [c] So we can evaluate how the agent behaves with and "
  "without the values."], None),
 (22, "We asked six types of question across 290 conversations", [
  "[c] We asked six types of questions, each with its own purpose: translate words into a lever, find what the "
  "surrogate can't report, find the levers that matter, [c] complete the RDM steps, compare without naming a "
  "winner, and say when the model can't answer. [c] In total, 29 question scripts, with both versions of the "
  "network, five times each: 290 conversations, all logged for the analysis."], None),
 (23, "Four criteria, each with its own objective", [
  "We evaluate each conversation on four criteria, each with its own objective. [c] Tool use: does the agent "
  "run the analysis correctly? We check that the lever level matches the key, that no required step is "
  "skipped, and that no failure threshold is invented. [c] Answer rules: can the user trace where the numbers "
  "come from? [c] Per question: did it deliver what that question needed? [c] And reader model: a second "
  "model checks that the conversation respects the RDM framing. We'll come back to these in the findings."], None),
 (24, "Each conversation is scored against a human answer key", [
  "[c] Each question is asked word for word. [c] Before the run, we wrote what we expected: the answer key and "
  "the tools. [c] Then we take what we observed from the log: the tools, the arguments and the answer. [c] And "
  "we compare the two, with 25 automatic checks."], None),
 (25, "Divider: Findings", ["Now, what did we find?"], None),
 (26, "With no values, the agent can only guess what words mean", [
  "Let me walk you through this one. Each line is the lever level, from 0 to 1. [c] The first question: what if half of rural households' wastewater went to septic "
  "tanks by 2050? [c] Half of households in septic tanks is a lever level of 0.72. That is our answer key, "
  "from the model runs. [c] With Map, the agent set 0.5 in all five conversations. It read 'half' as half of "
  "the lever. [c] With Map+, it set 0.72, five out of five.",
  "[c] The second question: what if Uganda's landfills captured 40% of the methane by 2050? The key is 0.69. "
  "[c] With Map, it set 0.4 once, and four times it ran 0.4, 0.7 and 1 without choosing. [c] With Map+, 0.69, "
  "five out of five. [c] With no values, the agent can only guess what words mean. With values, it looks them "
  "up."],
  "Lever levels from the first run of each conversation; keys computed from the runs and fixed before the experiment."),
 (27, "With values, the agent set levels right in fewer calls", [
  "And this holds across all the questions. [c] With Map, the policy level was off the answer key in 79% of "
  "answers. With Map+, in 1%. [c] And it got there with fewer calls to the network: 1.3 per conversation "
  "instead of 2.3. [c] With Map, half of the answers took the words literally: '40%' became 0.4. With Map+, "
  "none. [c] And with values, it used the trade-off tool for comparisons in 4 of 10 conversations; with Map, "
  "never."],
  "Rows 1–3: p < 0.01, over the 290 conversations."),
 (28, "With values, the agent also calculates for itself", [
  "[c] But with values, the agent also calculates for itself. Answers with a number that no tool gave went from 11 to 17 out of 155. [c] Here, for example, it "
  "divided 21 by 33 and said 'about 0.64 electric'. Reasonable, but no tool computed it, so it "
  "needs tracing before it reaches a decision maker."], None),
 (29, "With values, the agent can stop before the answer", [
  "And with values, the agent can stop too early. In four questions, the answer is a few steps along the "
  "network. [c] With Map, the agent reached the variable with the answer in 16 "
  "of 20 conversations. With Map+, only 7. [c] When Map+ got there, it always gave the value. When it stopped "
  "early, it never did. [c] Here it told the user that the tools don't report transport electricity demand. "
  "But the network had it, two steps further on. [c] The values answer the first step so well that it stops "
  "looking."], None),
 (30, "A simulated user worked through RDM via the agent", [
  "Now the first research question: can a non-technical user complete the three RDM components through the "
  "agent? The user here is scripted, not a real policy maker. [c] The user asks if a renewables and "
  "deforestation policy is robust. The agent runs it across 500 futures and asks what counts as failure. [c] "
  "Failure is 2050 emissions not at least 5% below business as usual. The policy fails in 79% of futures, mostly when GDP grows fast. [c] Does it "
  "still work if the economy grows fast? It fails in 99%. [c] Then: what could we change so it holds up? The "
  "agent goes back to the network, adds a livestock lever, and now it fails in 0%."], None),
 (31, "Across all 290 conversations, the process held", [
  "Across all 290 conversations: [c] all 290 finished. [c] The agent never "
  "invented a failure threshold. [c] And conversations that skipped a required RDM step went from 22% with Map "
  "to 12% with Map+."], None),
 (32, "What data the agent gets, and how, shapes how it behaves", [
  "[c] First, show values, not only "
  "links. The agent turns words into the right setting, from 79% to 1% off the key, and searches less, "
  "sometimes too little. [c] Second, trace every number: values invite the agent's own arithmetic. [c] Third, a "
  "simulated user can work through RDM with the agent, although 12% of conversations still skipped a required "
  "step.",
  "[c] These results are for one model, one country, one agent model and scripted users. Next, we want to "
  "test it with real users in Uganda.",
  "More information doesn't simply mean better. It changes how the agent behaves. So what data we give, and "
  "how we give it, is a design decision we have to test. Thank you."], None),
]


def words(paras):
    return sum(len(p.replace("[c]", "").split()) for p in paras)


def run(par, text, bold=False, color=None, size=13, italic=False):
    r = par.add_run(text)
    r.font.name, r.font.size, r.bold, r.italic = FONT, Pt(size), bold, italic
    if color is not None:
        r.font.color.rgb = color
    return r


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; write a new version instead of overwriting.")
    total = sum(words(p) for _, _, p, _ in S)
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    run(doc.add_paragraph(), "DMDU 2026 talk: speech draft (deck v9)", bold=True, size=18, color=BLUE)
    p = doc.add_paragraph()
    run(p, f"{total:,} words, about {total / WPM:.0f} minutes at {WPM} words per minute. ", size=11, color=GREY)
    run(p, "▶ ", bold=True, size=11, color=BLUE)
    run(p, "marks a click, in the order the slide builds. Grey lines are for Q&A, not to say aloud. "
           "Built from your comments and notes; change anything that doesn't sound like you.", size=11, color=GREY)
    for n, title, paras, qa in S:
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.keep_with_next = True
        run(h, f"Slide {n} · {title}", bold=True, size=13, color=BLUE)
        run(h, f"   ≈{round(words(paras) / WPM * 60 / 5) * 5} s", size=10, color=GREY)
        for para in paras:
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.35
            p.paragraph_format.space_after = Pt(6)
            parts = para.split("[c]")
            for i, part in enumerate(parts):
                if i:
                    run(p, " ▶ ", bold=True, color=BLUE)
                run(p, part.strip() if i else part.rstrip())
        if qa:
            p = doc.add_paragraph()
            run(p, "If asked: " + qa, size=10, color=GREY, italic=True)
    doc.save(OUT)
    print(OUT, total, "words", f"{total / WPM:.1f} min")
    for n, _, paras, _ in S:
        print(n, words(paras), f"{words(paras) / WPM * 60:.0f}s")


if __name__ == "__main__":
    main()
