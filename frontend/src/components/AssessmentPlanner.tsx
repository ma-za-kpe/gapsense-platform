import { useReducer, useState } from "react";

import type { Analytics } from "../analytics/client";
import { buildSampleActivity, publicSampleProfiles } from "../domain/sampleActivity";
import {
  clearSampleDraft,
  type DraftStorage,
  readSampleDraft,
  saveSampleDraft,
  type SampleDraftRecovery,
} from "../domain/sampleDraft";
import {
  countryProfiles,
  goalProfiles,
  isPlanComplete,
  plannerReducer,
  roleProfiles,
  type Country,
  type Goal,
  type PlannerAction,
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

type AssessmentPlannerProps = {
  readonly analytics: Analytics;
  readonly onOpenAssessment: () => void;
  readonly storage?: DraftStorage;
};

const recoveryMessage = (recovery: SampleDraftRecovery): string | null => {
  switch (recovery) {
    case "restored":
      return "Restored your saved sample choice on this device.";
    case "discarded":
      return "A saved choice could not be restored and was safely cleared.";
    case "unavailable":
      return "This browser cannot save your choice; keep this tab open.";
    case "empty":
      return null;
  }
};

export function AssessmentPlanner({
  analytics,
  onOpenAssessment,
  storage = window.localStorage,
}: AssessmentPlannerProps): React.JSX.Element {
  const [restored] = useState(() => readSampleDraft(storage));
  const [state, dispatch] = useReducer(plannerReducer, restored.draft);
  const [recovery, setRecovery] = useState<SampleDraftRecovery>(restored.recovery);
  const complete = isPlanComplete(state);
  const reviewedPlan = state.reviewed && complete ? state : null;
  const sample =
    reviewedPlan === null ? null : buildSampleActivity(reviewedPlan.role, reviewedPlan.country);

  const updatePlan = (action: PlannerAction): void => {
    const nextState = plannerReducer(state, action);
    dispatch(action);
    if (!saveSampleDraft(storage, nextState)) setRecovery("unavailable");
  };

  return (
    <section className="planner section-shell" id="planner" aria-labelledby="planner-heading">
      <div className="section-heading planner__heading">
        <span className="eyebrow">Start with intent</span>
        <h2 id="planner-heading">Choose the learning job before the material.</h2>
        <p>
          Choose who it is for, the country context, and what you need. Practice is available as an
          illustrative sample today. Diagnostic reasoning and complete assessment packages stay
          visible, but locked until their evidence and review gates pass.
        </p>
      </div>

      {recoveryMessage(recovery) === null ? null : (
        <p className="draft-recovery" role="status">
          {recoveryMessage(recovery)}
        </p>
      )}

      <form
        className="planner__form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!complete) return;
          analytics.track("planner_reviewed");
          updatePlan({ type: "review" });
        }}
      >
        <fieldset className="choice-group">
          <legend>
            <span className="step-number">01</span>
            Who will use the sample?
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
                    updatePlan({ type: "select-role", role: value });
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
            Choose an illustrative context
          </legend>
          <div className="choice-grid choice-grid--countries">
            {countries.map(([value, profile]) => {
              const sampleProfile = publicSampleProfiles[value];
              return (
                <label className={`country-choice country-choice--${profile.accent}`} key={value}>
                  <input
                    type="radio"
                    name="country"
                    value={value}
                    checked={state.country === value}
                    onChange={() => {
                      analytics.track("planner_country_selected");
                      updatePlan({ type: "select-country", country: value });
                    }}
                  />
                  <span className="country-choice__body">
                    <span className="country-choice__topline">
                      <strong>{profile.name}</strong>
                      <span>{profile.authority}</span>
                    </span>
                    <small>{profile.authorityLongName}</small>
                    <span className="sample-context">
                      Sample context: {sampleProfile.level} {sampleProfile.subject}
                    </span>
                    <span className="coverage-note">
                      <span aria-hidden="true" /> Not curriculum-aligned or educator-reviewed
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <fieldset className="choice-group">
          <legend>
            <span className="step-number">03</span>
            What should this help you do?
          </legend>
          <div className="choice-grid choice-grid--goals">
            {goals.map(([value, profile]) => (
              <label
                className={`choice-card choice-card--goal${profile.available ? "" : " choice-card--unavailable"}`}
                key={value}
              >
                <input
                  type="radio"
                  name="goal"
                  value={value}
                  checked={state.goal === value}
                  disabled={!profile.available}
                  onChange={() => {
                    analytics.track("planner_goal_selected");
                    updatePlan({ type: "select-goal", goal: value });
                  }}
                />
                <span className="choice-card__body">
                  <span className="choice-card__check" aria-hidden="true" />
                  <strong>{profile.label}</strong>
                  <small>{profile.note}</small>
                  {profile.status === undefined ? null : (
                    <span className="choice-card__status">{profile.status}</span>
                  )}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="planner__action-row">
          <p>
            <span className="privacy-dot" aria-hidden="true" /> Saved on this device. No name,
            school, account, or learner response.
          </p>
          <button className="button button--primary" type="submit" disabled={!complete}>
            Review sample choice
          </button>
        </div>
      </form>

      {reviewedPlan === null || sample === null ? null : (
        <article className="plan-review" aria-live="polite">
          <div className="plan-review__icon" aria-hidden="true">
            <span />
          </div>
          <div className="plan-review__content">
            <span className="eyebrow">Saved sample choice</span>
            <h3>Your {sample.country} sample is ready</h3>
            <p className="plan-review__selection">
              {roleProfiles[reviewedPlan.role].label} · {goalProfiles[reviewedPlan.goal].label}
            </p>
            <p>
              {sample.level} {sample.subject} · {sample.roleGuidance}
            </p>
            <p className="evidence-boundary">{sample.provenance}</p>
            <button
              className="button button--primary"
              type="button"
              onClick={() => {
                if (!saveSampleDraft(storage, reviewedPlan)) setRecovery("unavailable");
                analytics.track("sample_opened");
                onOpenAssessment();
              }}
            >
              Open sample activity
            </button>
          </div>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => {
              analytics.track("planner_reset");
              clearSampleDraft(storage);
              setRecovery("empty");
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
