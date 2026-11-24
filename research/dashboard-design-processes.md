# Dashboard design processes worth trialling against the house Design step

Research for [#127](https://github.com/dempseydata/hindsight/issues/127). Checked 2026-11-24 against the primary sources cited inline.

**Key:** **[V]** verified: stated in the cited primary source. **[I]** inferred: my reasoning from verified facts, not stated by any source.

## Answer

Trial **two** processes, with an optional third:

1. **Few's requirements front-end** (*Information Dashboard Design*, 2nd ed., ch. 3–4, and his Dashboard Design Requirements Questionnaire), with his **thirteen common mistakes** (ch. 2) added to the Audit step. It asks, in writing and before any layout, who uses the dashboard, what questions it answers and **what actions follow from the answers**, then which data items, which are key, how they group, what each is compared with, and what counts as an exception. One user can answer it alone. Its action question is hindsight's blind *would I act on this?* rating written as a requirement, so the trial costs little and tests whether the rating gets better when it is done first and in writing.
2. **Bach et al.'s staged dashboard process** (Dashboard Design Patterns, VIS 2022). It runs context → data & information → structure → visual representations → page layout → screenspace → interactivity, and adds a tradeoff model in which screenspace, abstraction, page count and interaction can only be cut by raising another. It replaces the house flow's optional step 2 (Wireframe) for dashboards. Its screenspace stage and tradeoff model are where hindsight's v1 failure sat: the restyle cut What's above-the-fold rows from 11 to 3, and the house flow has no step that makes that tradeoff explicit.
3. *(Optional)* **Five Design-Sheets** (Roberts et al., TVCG 2016) as a cheaper Diverge for **structure**: one brainstorm sheet, three design sheets and one realization sheet, sketched by hand. Trial it only if a new view, not the restyle, is the subject.

Use **Munzner's nested model** as the frame for judging the trial, not as a candidate. Its four levels and the threats at each (wrong problem, wrong abstraction, ineffective encoding, slow algorithm) tell you which level a trial result speaks to. Do not trial **Sedlmair et al.'s design study methodology** whole: it is a research method for collaborations with domain experts, and most of its precondition stages have nothing to do for one user who is also the builder. Six of its 32 pitfalls do apply; see *Sedlmair*.

**A flaw in the trial as framed [I].** Every established dashboard process found here decides content and structure first and leaves look last or subordinate. The house Design flow is mostly look: Taste, five directions, narrowing, tokens, assets, tweaks. The restyle now underway ([#128](https://github.com/dempseydata/hindsight/issues/128)) has its density and meaning frozen by the floor in [#126](https://github.com/dempseydata/hindsight/issues/126). A dashboard process trialled on that restyle can therefore only re-confirm decisions already fixed, and it will look like a no-op. Run the trial on a **new view**, with the errors-by-consumer view (ADR-0026, v2-framing lesson 9) the obvious candidate, or accept that on the restyle it tests only the screenspace and audit stages.

## The house baseline being compared against

`my-standards/my-process.md` → Design (house process, not in this repo): Taste → optional Wireframe → Diverge (5 directions) → Narrow (pick 1, then 3 variants) → System (tokens) → Assets → Tweak → Audit. For dense tool UIs there is also a "prototype-first" rule: build the data pipeline, then make throwaway greybox screens over **real data** to settle density, hierarchy and empty/error states before any direction is set.

Hindsight-specific constraints any candidate has to respect:

- **v2-framing lesson 10:** run a blind *would I act on this?* rating on rendered sentences over real data before any layout. ADR-0026 rated 18 rows and got 1 *act*, and the view was dropped (`background/ideation/v2-framing.md`, `docs/adr/0026-*`).
- **Lesson 11:** chrome cost more than it returned for one user, and the v1 restyle (ADR-0029) cut the ledger rows above the fold from 11 to 3.
- **The #126 floor:** a restyle may change the look but may not reduce density or change meaning. Each view has numeric above-the-fold floors at 1440 × 900.

## The candidates

### 1. Stephen Few: information dashboard design practice

**Sources.** Few, *Information Dashboard Design: Displaying Data for At-a-Glance Monitoring*, 2nd ed., Analytics Press, 2013. TOC from the publisher: <https://analyticspress.com/images/IDD-TOC.pdf>. Few, *Dashboard Design Requirements Questionnaire*: <https://www.perceptualedge.com/articles/misc/Dashboard_Design_Requirements_Questionnaire.pdf>. Few, *Common Pitfalls in Dashboard Design*, 2006: <https://www.perceptualedge.com/articles/Whitepapers/Common_Pitfalls.pdf>. Few, *Dashboard Confusion Revisited*, 2007: <https://www.perceptualedge.com/articles/visual_business_intelligence/dboard_confusion_revisited.pdf>.

**What it asks for, in order [V].** The book's chapter order is the process:
1. Clarify what a dashboard is (ch. 1). Few defines it as a display of the most important information needed to reach one or more objectives, arranged on a single screen so it can be monitored at a glance (*Dashboard Confusion Revisited*).
2. Know the thirteen common mistakes (ch. 2). The first is exceeding a single screen. Others include inadequate context, excessive detail, meaningless variety, useless decoration and misused colour (*Common Pitfalls*, pp. 4–14).
3. **Assess what's needed** before design begins (ch. 3).
4. **Fundamental considerations:** frequency of use, who uses it and how experienced they are, screen size, and the type of data (ch. 4).
5. Perception, simplicity, graphics, a library of graphs, bullet graphs, sparklines and other media (ch. 5–11).
6. Critical design practices (ch. 12) and worked examples (ch. 13).
7. **From imagining to unveiling:** the design process, introducing the design to users and confirming that it works (ch. 14).

The requirements questionnaire is the concrete artefact for steps 3–4. It asks eight questions in order: update frequency; who uses it; what they use it to do, **which questions it answers and what actions they take in response**; every data item and its level of detail; which items are key; their logical groupings; the useful comparisons (targets, history); and what counts as an exception for each item.

**What it produces [V/I].** A written requirements sheet: items, key items, groups, comparisons and exception thresholds. Then a single-screen design checked against the thirteen mistakes. The checklist use is my inference [I]. The book's chapter 14 covers the process steps, but I have only its TOC summary, not its text.

**Evidence base [V/I].** Practitioner synthesis from Few's consulting and teaching, grounded in the perception research he cites. It is not an empirical study of the process [I]. Bach et al. use Few's definition as the reference point for their "analytic" genre, which is 73% of their corpus (Bach et al. §4).

**Fit for one user who builds [I].** Good. The questionnaire is addressed to a client, but every question can be answered by the operator in ten minutes. Nothing degrades except question 2 ("who uses it"), which collapses to one known answer. Question 3's action clause **is** lesson 10's act-rating, asked up front. Question 8 (exceptions) matches how hindsight already uses the amber/caution form (ADR-0029 §8). The single-screen ideal conflicts with What's 4468px page height. That conflict is worth surfacing as a trial finding, not resolving in advance.

**Where it slots [I].** It goes ahead of Taste for any dashboard view, as a written input note (the house process already allows "a design-phase input note"). The thirteen mistakes join `/impeccable audit` at step 8. They are content checks the floor does not cover.

### 2. Bach et al.: dashboard design patterns and their design process

**Sources.** Bach, Freeman, Abdul-Rahman, Turkay, Khan, Fan, Chen, *Dashboard Design Patterns*, IEEE VIS 2022 (TVCG 2023), Best Paper Honourable Mention: <https://arxiv.org/abs/2205.00757>. Process page: <https://dashboarddesignpatterns.github.io/processguidelines.html>. Site: <https://dashboarddesignpatterns.github.io>.

**What it asks for, in order [V]** (process page):
- **Stage 0, context:** the audience and what they know, the viewing situation (device, time available, frequency), the tasks and decisions to support (look up, compare, analyse), and the information needed.
- **Stage 1, data & information:** which information matters for those tasks, and at what level of detail or abstraction.
- **Stage 2, structure:** one page or several, and how pages relate (parallel or hierarchical).
- **Stage 3, visual representations** per page.
- **Stage 4, page layout:** relationships between components and their priority.
- **Stage 5, screenspace:** whether everything fits on one screen or must be revealed on demand. Analytic dashboards should avoid overflow that hinders comparison.
- **Stage 6, interactivity:** only what a static solution cannot do.

The stages are guides and iterate. The paper states that the process assumes requirements analysis has already defined users, tasks and data (§7.3). The 42 patterns fall into 8 groups. Content patterns cover data information, meta information and visual representation. Composition patterns cover page layout, screenspace, structure, interaction and colour (§1). The tradeoff model (§5, Fig. 6) says that reducing one of screenspace, abstraction, number of pages or interaction requires raising another.

**What it produces [V].** A documented decision for each stage, which participants described as "a written plan for your dashboard" (§6.2.3, participant quote). Then mockups (Figma in the workshop).

**Evidence base [V].** The patterns come from a coded corpus of 144 dashboards (§3), the authors' experience building over 7,000 Covid-19 dashboards (§5), and a two-week workshop with 23 participants (§6). The **process itself was introduced and discussed in the workshop, not evaluated** against an alternative. The evidence for the patterns is strong; the evidence for the process is weak [I].

**Fit for one user who builds [I].** Good. Stage 0 is the only stage that assumes stakeholders, and it shrinks to one operator. The rest are design decisions the builder owns. The paper says the patterns support "lower-level design decisions that the dashboard designer actually has agency over" (§5), which is exactly the solo case. Hindsight's views map onto its genres. What and Where are analytic dashboards. How's Status is closest to a screenfit / single-value composition.

**Where it slots [I].** It replaces the optional step 2 (Wireframe) for dashboard surfaces, and makes it **mandatory**. The house text already says step 2 "is where its real decisions actually get made" for dense tool UIs. Stage 5 (screenspace) and the tradeoff model are where the #126 density figures belong: they become a stated constraint of the layout stage, not a regression test after styling. The colour pattern group overlaps the house floor (semantic roles, chart palette) and adds nothing new.

### 3. Munzner: the nested model and what–why–how

**Sources.** Munzner, *A Nested Model for Visualization Design and Validation*, IEEE TVCG 15(6), 2009 (InfoVis Ten-Year Test of Time award, 2019): <https://www.cs.ubc.ca/labs/imager/tr/2009/NestedModel/>. Munzner, *Visualization Analysis and Design*, CRC Press, 2014, ch. 2 "What: Data Abstraction", ch. 3 "Why: Task Abstraction", ch. 4 "Analysis: Four Levels for Validation": <https://www.cs.ubc.ca/~tmm/vadbook/>. Brehmer & Munzner, *A Multi-Level Typology of Abstract Visualization Tasks*, TVCG 19(12), 2013: <https://www.cs.ubc.ca/labs/imager/tr/2013/MultiLevelTaskTypology/>.

**What it asks for, in order [V].** Four nested levels, each feeding the next:
1. Characterise the domain problem and data.
2. Abstract them into operations and data types.
3. Design the visual encoding and interaction.
4. Implement the algorithm.

Each level has its own threat to validity (2009 paper, Fig. 2, §3.3–3.6):
- **Wrong problem.** Immediate validation: observe and interview target users. Downstream validation: adoption.
- **Bad abstraction.** Validated downstream by target users doing their own work, and by field study.
- **Ineffective encoding.** Immediate validation: justify against perceptual principles, heuristic evaluation, expert review. Downstream validation: lab study, analysis of result images.
- **Slow algorithm.** Validated by complexity analysis and measured timings.

The paper stresses that the levels are rarely done in strict sequence, and that rapid prototyping exists "exactly so that downstream validation can occur sooner" (§3.2). Brehmer & Munzner split each task into **why** (purpose), **how** (method) and **what** (inputs and outputs).

**What it produces [V/I].** A named abstraction (data types, task verbs) and a validation plan for each level. It is an analysis framework and does not lay out a design workflow [I].

**Evidence base [V].** A conceptual model, illustrated by worked analyses of published papers (§4). It is widely adopted, as the award shows.

**Fit for one user who builds [I].** Good as a lens, poor as a process. The domain-level validation ("interview and observe target users") degrades to self-observation, and hindsight already instruments that (serve.log as the view-use record, commit c0fb474). Lesson 10's blind rating is an **abstraction-level, downstream** validation: the target user, on real data, judges whether the output supports their own work. ADR-0026 is a clean instance of the model catching a wrong-problem or bad-abstraction failure before any encoding work. That is the case for using it to classify trial results: a trial that changes encoding but not abstraction cannot fix a 1-in-18 act rate.

### 4. Sedlmair, Meyer & Munzner: design study methodology

**Source.** *Design Study Methodology: Reflections from the Trenches and the Stacks*, IEEE TVCG 18(12), 2012: <https://www.cs.ubc.ca/labs/imager/tr/2012/dsm/>.

**What it asks for, in order [V].** Nine stages in three phases:
- **Precondition:** learn, winnow, cast.
- **Core:** discover, design, implement, deploy.
- **Analysis:** reflect, write.

The paper lists 32 pitfalls, one or more per stage (Table 1). The design stage asks for a broad "consideration space", filtered to a narrow "proposal space" that is shown to experts as paper mockups, data sketches or low-fidelity prototypes (§4.2.2). Implementation calls for rapid, throwaway prototypes (§4.2.3).

**Evidence base [V].** The authors' 21 design studies plus a literature review.

**Fit for one user who builds [I].** Poor as a whole. Learn, winnow, cast, write and much of discover assume a researcher and separate domain experts. These pitfalls transfer directly:
- **PF-1**, premature advance: jumping over stages.
- **PF-4**, no real data: hindsight's prototype-first rule already answers this.
- **PF-14**, "mistaking fellow tool builders for real end users". Here the builder *is* the user, which is the self-deception risk.
- **PF-20**, consideration space too small.
- **PF-22**, non-rapid prototyping.
- **PF-26**, "liking necessary but not sufficient for validation": demand characteristics.

PF-26 is the strongest argument for keeping hindsight's ratings **blind**.

**Where it slots [I].** Nowhere as a process. Add PF-20 and PF-26 to the trial's own review checklist.

### 5. Lam, Tory & Munzner: from goals to tasks

**Source.** *Bridging From Goals to Tasks with Design Study Analysis Reports*, IEEE InfoVis 2017. Abstract: <https://www.tableau.com/research/publications/bridging-goals-tasks-design-study-analysis-reports>. I read the abstract, not the full paper.

**What it asks for [V, abstract only].** First name the analysis goal of each unit of analysis on two axes. One axis is specificity: explore, describe, explain, confirm. The other is the number of data populations: single or multiple. Nine goals in all. Then encode each step with an existing task typology. The evidence is the open coding of 20 design-study papers from InfoVis 2009–2015.

**Fit [I].** A useful vocabulary for Few's question 3 and Bach's Stage 0. Not a process to trial in its own right.

### 6. Wexler, Shaffer & Cotgreave: *The Big Book of Dashboards*

**Source.** Wiley, 2017. TOC from the publisher: <https://www.wiley.com/en-us/The+Big+Book+of+Dashboards%3A+Visualizing+Your+Data+Using+Real+World+Business+Scenarios-p-9781119282716>.

**What it is [V].** A catalogue, not a process. Part I is a visualization primer (ch. 1). Part II is 28 real-world scenarios (ch. 2–29), including "Server Process Monitoring" (ch. 18). Part III, "Succeeding in the Real World", covers personal dashboards, visualising time, "Beware the Dead-End Dashboard", red/green, pies and donuts, clouds and bubbles, and a closing chapter (ch. 30–36). The authors' site says the companion *Dashboards That Deliver* (2025) covers the lifecycle from idea through discovery, prototyping, release and maintenance (<https://www.bigbookofdashboards.com/>).

**Fit [I].** Good as Taste-step reference material for a monitoring view, which closes part of the house process's "standing gap" for dashboards specifically. **Not reachable:** I could not read the book's text or *Dashboards That Deliver*, so I cannot state their question-first process primarily. They are dropped as process candidates on that ground, not on merit.

### 7. Roberts et al.: Five Design-Sheets

**Sources.** Roberts, Headleand, Ritsos, *Sketching Designs Using the Five Design-Sheet Methodology*, IEEE TVCG 22(1), 2016, doi:10.1109/TVCG.2015.2467271. Author's version: <https://hccbu.github.io/files/Roberts-et-al-TVCG-2016.pdf>. The original is Roberts, Eurographics 2011 Education, doi:10.2312/EG2011/education/029-036. The former method site `fds.design` now redirects to an unrelated domain.

**What it asks for, in order [V].** First, a preamble:
- **Data:** the method assumes data exists, and "it is impossible to continue" without it.
- **Task.**
- **Components:** variables, types, categories, temporal aspects.

Then five sheets:
- **Sheet 1** is the brainstorm: ideas, filter, categorise, combine & refine, question.
- **Sheets 2–4** are three principal designs. Each has layout, operations (action ⇒ result pairs), focus/parti, and a discussion of fit to task, feasibility and scalability.
- **Sheet 5** is the realization design, which is then implemented (§3).

The discussion can be held with a client or alone (§3).

**What it produces [V].** Five paper sheets, the last a buildable specification.

**Evidence base [V].** About five years of teaching use. A modified System Usability Scale returned 74.29 ("good") from 21 usable responses out of 53 module students (§4.1). There was also an industry case study, and a comparison of FdS quality with module marks. That is evidence that the method is usable; it says nothing about the outcome compared with other methods [I].

**Fit for one user who builds [I].** Fair. It is explicitly solo-capable, real-data-first, and decides structure and interaction rather than look. Its three designs are a cheaper Diverge than five comps. The authors also warn that wireframing software "can restrict rather than engender the creative process" (§3.1), which is a direct counterpoint to using Claude Design for step 2. The risk is that hand sketches cannot answer "does this read at 40 real rows". Pair it with the greybox, never instead of it.

### 8. Designing over real data: the evidence, not a process

No primary source found here offers a named "wireframe over real data" **process**. Two primary studies supply the evidence that hindsight's prototype-first rule rests on:

- **Bigelow, Drucker, Fisher, Meyer**, *Reflections on How Designers Design With Data*, AVI 2014 (Best Paper): <https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/design-vis.pdf>. In observations and interviews with fifteen designers [V]:
  - designers sketch from *perceived* data behaviour (P1);
  - those inferences "were often inaccurate" (P2), and in one case a misread record caused a complete redesign;
  - layout, typefaces and colour schemes were settled "long before" real data was placed (P7).
- **Walny et al.**, *Data Changes Everything: Challenges and Opportunities in Data Visualization Design Handoff*, IEEE TVCG 26(1), 2020: <https://arxiv.org/abs/1908.00192>. Drawn from five large projects, it lists six data-specific challenges [V]:
  - adapting to data changes;
  - anticipating edge cases;
  - understanding technical constraints;
  - articulating data-dependent interactions;
  - communicating data mappings;
  - preserving mapping integrity across iterations.

**Fit [I].** Bigelow's P7 describes the v1 restyle failure exactly: look was decided first, and real data at real density arrived afterwards. These papers support **keeping** the house prototype-first rule and its "real content in the comps" clause, and they say Diverge/Narrow comps must be fed hindsight's real rows, not samples. Hindsight already does this, so there is nothing to trial. I did not read data-driven design *tools* (Lyra, Data Illustrator) as processes. They are authoring tools, and ADR-0008 (no build step, no CDN) rules out adopting one anyway.

## How the recommended trial would run [I]

Run it on one new view, with errors by consumer as the candidate:

1. **Few's questionnaire**, written down, with the act question answered per data item. Then the existing blind act-rating on rendered sentences over real data. Kill or keep here (lesson 10). *Compare:* does writing the questionnaire first change the act rate, or which items get rated?
2. **Bach stages 1–6** as the wireframe step, in a throwaway greybox over real data (prototype-first, Impeccable hooks off). Record each stage's decision, and the screenspace tradeoff against the #126-style density figures. *Compare:* rows above the fold, and the decisions made, against a view designed through the current step 2.
3. *(Optional)* **FdS sheets 1–5** before or instead of Diverge's five comps, for structure only. Look still comes from steps 3–7.
4. **Audit:** the house floor plus Few's thirteen mistakes plus Sedlmair PF-20 and PF-26.
5. Classify every finding by **nested-model level**, so a look-level win is not mistaken for an abstraction-level one.

Steps 3–8 of the house flow (Diverge through Audit) are unchanged for look. None of these processes competes with them, which is the finding.

## Not reached or dropped

- *The Big Book of Dashboards* text and *Dashboards That Deliver*: only the publisher's TOC and the authors' site were readable. Dropped as process sources.
- Few's book text (ch. 3, 4, 14): only the publisher's TOC summaries and Few's own articles and questionnaire were read. The chapter-14 process steps are not reproduced here for that reason.
- Lam, Tory & Munzner 2017: abstract only.
- The Bach et al. process page was read on the project site. The paper itself (§7.3) describes it as "one possible design process" and points to the site.
- `fds.design`: the domain no longer belongs to the method. The author's-version PDF was used instead.
