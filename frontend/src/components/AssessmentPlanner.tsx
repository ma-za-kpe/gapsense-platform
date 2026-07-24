import { useReducer, useState } from "react";

import type { Analytics } from "../analytics/client";
import {
  countryProfiles,
  goalProfiles,
  initialPlan,
  isPlanComplete,
  plannerReducer,
  roleProfiles,
  type Country,
  type Goal,
  type Role,
} from "../domain/planner";

const roles = Object.entries(roleProfiles) as readonly (readonly [
  Role,
  (typeof roleProfiles)[Role],
])[];
const countries = Object.entries(countryProfiles) as readonly (readonly [
  Country,
  (typeof countryProfiles)[Country],
])[];
const goals = Object.entries(goalProfiles) as readonly (readonly [
  Goal,
  (typeof goalProfiles)[Goal],
])[];

const starterCatalog = {
  ghana: {
    levels: ["Basic 1", "Basic 2", "Basic 3", "Basic 4", "Basic 5", "Basic 6"],
    subjects: ["Mathematics", "English Language", "Science"],
  },
  uganda: { levels: ["Primary 1", "Primary 2", "Primary 3"], subjects: ["Mathematics"] },
} as const;

const starterQuestions = {
  Mathematics: [
    "Write the number that comes immediately after 19.",
    "Amina has 7 mangoes and receives 5 more. How many mangoes does she have now?",
    "Circle the greater number: 34 or 43.",
    "Share 12 pencils equally between 3 learners. How many does each learner get?",
    "Complete the pattern: 2, 4, 6, __, __.",
  ],
  "English Language": [
    "Write one sentence that uses the word ‘school’.",
    "Circle the noun: The bright bird sings.",
    "Write the plural of ‘book’.",
    "Put these words in order: is / kind / Kojo.",
    "Write one word that rhymes with ‘cat’.",
  ],
  Science: [
    "Name one source of light.",
    "Which sense do we use to hear sounds?",
    "Name one thing a plant needs to grow.",
    "Is water a solid, liquid, or gas at room temperature?",
    "Name one animal that lives in your community.",
  ],
} as const;
const answerGuidance: Record<keyof typeof starterQuestions, readonly string[]> = {
  Mathematics: ["20", "12 mangoes", "43", "4 pencils", "8, 10"],
  "English Language": ["Any clear sentence", "bird", "books", "Kojo is kind.", "bat (example)"],
  Science: ["The sun (example)", "hearing", "water (example)", "liquid", "Any local animal"],
};

type AssessmentPlannerProps = {
  readonly analytics: Analytics;
};

export function AssessmentPlanner({ analytics }: AssessmentPlannerProps): React.JSX.Element {
  const [state, dispatch] = useReducer(plannerReducer, initialPlan);
  const [level, setLevel] = useState("Basic 1");
  const [subject, setSubject] = useState<keyof typeof starterQuestions>("Mathematics");
  const [generated, setGenerated] = useState(false);
  const [shareStatus, setShareStatus] = useState<"idle" | "shared" | "copied">("idle");
  const complete = isPlanComplete(state);
  const reviewedPlan = state.reviewed && complete ? state : null;
  const catalog = state.country === null ? starterCatalog.ghana : starterCatalog[state.country];

  return (
    <section className="planner section-shell" id="planner" aria-labelledby="planner-heading">
      <div className="section-heading planner__heading">
        <span className="eyebrow">Free assessment planner</span>
        <h2 id="planner-heading">Start with intent, not a blank prompt.</h2>
        <p>
          Tell us three things. GapSense will preserve the country, curriculum, and purpose behind
          every future activity or assessment—without asking who the learner is.
        </p>
      </div>

      <form
        className="planner__form"
        onSubmit={(event) => {
          event.preventDefault();
          if (complete) {
            analytics.track("planner_reviewed");
          }
          dispatch({ type: "review" });
        }}
      >
        <fieldset className="choice-group">
          <legend>
            <span className="step-number">01</span>
            Who are you planning for?
          </legend>
          <div className="choice-grid choice-grid--roles">
            {roles.map(([value, profile]) => (
              <label className="choice-card" key={value}>
                <input
                  type="radio"
                  name="role"
                  value={value}
                  checked={state.role === value}
                  onChange={() => {
                    analytics.track("planner_role_selected");
                    dispatch({ type: "select-role", role: value });
                  }}
                />
                <span className="choice-card__body">
                  <span className="choice-card__check" aria-hidden="true" />
                  <strong>{profile.label}</strong>
                  <small>{profile.note}</small>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="choice-group">
          <legend>
            <span className="step-number">02</span>
            Choose the education system
          </legend>
          <div className="choice-grid choice-grid--countries">
            {countries.map(([value, profile]) => (
              <label className={`country-choice country-choice--${profile.accent}`} key={value}>
                <input
                  type="radio"
                  name="country"
                  value={value}
                  checked={state.country === value}
                  onChange={() => {
                    analytics.track("planner_country_selected");
                    setLevel(starterCatalog[value].levels[0]);
                    setSubject(starterCatalog[value].subjects[0]);
                    setGenerated(false);
                    setShareStatus("idle");
                    dispatch({ type: "select-country", country: value });
                  }}
                />
                <span className="country-choice__body">
                  <span className="country-choice__topline">
                    <strong>{profile.name}</strong>
                    <span>{profile.authority}</span>
                  </span>
                  <small>{profile.authorityLongName}</small>
                  <span className="level-list">{profile.levels.join(" · ")}</span>
                  <span className="coverage-note">
                    <span aria-hidden="true" /> Inventory and review in progress
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="choice-group">
          <legend>
            <span className="step-number">03</span>
            What should this help you do?
          </legend>
          <div className="choice-grid choice-grid--goals">
            {goals.map(([value, profile]) => (
              <label className="choice-card choice-card--goal" key={value}>
                <input
                  type="radio"
                  name="goal"
                  value={value}
                  checked={state.goal === value}
                  onChange={() => {
                    analytics.track("planner_goal_selected");
                    dispatch({ type: "select-goal", goal: value });
                  }}
                />
                <span className="choice-card__body">
                  <span className="choice-card__check" aria-hidden="true" />
                  <strong>{profile.label}</strong>
                  <small>{profile.note}</small>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="planner__action-row">
          <p>
            <span className="privacy-dot" aria-hidden="true" /> No name, phone number, school, or
            account required.
          </p>
          <button className="button button--primary" type="submit" disabled={!complete}>
            Review my starting point
            <span aria-hidden="true">→</span>
          </button>
        </div>
      </form>

      {reviewedPlan === null ? null : (
        <article className="plan-review" aria-live="polite">
          <div className="plan-review__icon" aria-hidden="true">
            <span />
          </div>
          <div className="plan-review__content">
            <span className="eyebrow">Private local plan</span>
            <h3>Your {countryProfiles[reviewedPlan.country].name} starting point is ready</h3>
            <p className="plan-review__selection">
              {roleProfiles[reviewedPlan.role].label} · {goalProfiles[reviewedPlan.goal].label}
            </p>
            <p>
              {countryProfiles[reviewedPlan.country].authority} curriculum inventory is still being
              verified. This local prototype uses a small, deterministic starter bank while that
              work continues; it never presents this draft as an official examination.
            </p>
            <div className="starter-builder" aria-label="Build a starter activity">
              <label>
                Level
                <select
                  value={level}
                  onChange={(event) => {
                    setLevel(event.target.value);
                    setGenerated(false);
                  }}
                >
                  {catalog.levels.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label>
                Subject
                <select
                  value={subject}
                  onChange={(event) => {
                    setSubject(event.target.value as keyof typeof starterQuestions);
                    setGenerated(false);
                  }}
                >
                  {catalog.subjects.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              </label>
              <button
                className="button button--primary"
                type="button"
                onClick={() => setGenerated(true)}
              >
                Generate starter activity <span aria-hidden="true">→</span>
              </button>
            </div>
            {generated ? (
              <div className="starter-activity" aria-live="polite">
                <div className="starter-activity__header">
                  <div>
                    <span className="eyebrow">Local draft · {level}</span>
                    <h4>
                      {subject} {goalProfiles[reviewedPlan.goal].label}
                    </h4>
                  </div>
                  <div className="starter-activity__actions">
                    <button
                      className="button button--secondary"
                      type="button"
                      onClick={() => window.print()}
                    >
                      Print / save PDF
                    </button>
                    <button
                      className="button button--secondary"
                      type="button"
                      onClick={() => {
                        const shareText = `GapSense ${countryProfiles[reviewedPlan.country].name} ${level} ${subject} ${goalProfiles[reviewedPlan.goal].label} · local prototype`;
                        if (typeof navigator.share === "function") {
                          void navigator
                            .share({ title: "GapSense starter activity", text: shareText })
                            .then(() => setShareStatus("shared"))
                            .catch(() => undefined);
                        } else {
                          const clipboard = Reflect.get(navigator, "clipboard") as
                            { readonly writeText?: (text: string) => Promise<void> } | undefined;
                          if (typeof clipboard?.writeText === "function") {
                            void clipboard
                              .writeText(shareText)
                              .then(() => setShareStatus("copied"))
                              .catch(() => undefined);
                          }
                        }
                      }}
                    >
                      Share
                    </button>
                  </div>
                </div>
                <ol>
                  {starterQuestions[subject].map((question) => (
                    <li key={question}>
                      {question}
                      <span className="answer-line" />
                    </li>
                  ))}
                </ol>
                <aside className="activity-provenance" aria-label="Question organization">
                  <strong>How this draft is organised</strong>
                  <span>
                    Country: {countryProfiles[reviewedPlan.country].name} · Authority:{" "}
                    {countryProfiles[reviewedPlan.country].authority}
                  </span>
                  <span>
                    Level: {level} · Subject: {subject}
                  </span>
                  <span>Source status: local prototype bank; educator review pending</span>
                </aside>
                <details>
                  <summary>Show answer guidance</summary>
                  <ol>
                    {answerGuidance[subject].map((answer) => (
                      <li key={answer}>{answer}</li>
                    ))}
                  </ol>
                </details>
                <p className="starter-activity__note">
                  Prototype content for local testing. Curriculum alignment and educator review are
                  tracked separately in the evidence repository.
                </p>
                {shareStatus !== "idle" ? (
                  <p className="share-status" role="status">
                    {shareStatus === "shared"
                      ? "Share sheet opened."
                      : "Share text copied to your clipboard."}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => {
              analytics.track("planner_reset");
              setGenerated(false);
              setShareStatus("idle");
              dispatch({ type: "reset" });
            }}
          >
            Start again
          </button>
        </article>
      )}
    </section>
  );
}
