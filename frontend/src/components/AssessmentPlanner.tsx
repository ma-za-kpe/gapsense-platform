import { useReducer } from "react";

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

export function AssessmentPlanner(): React.JSX.Element {
  const [state, dispatch] = useReducer(plannerReducer, initialPlan);
  const complete = isPlanComplete(state);
  const reviewedPlan = state.reviewed && complete ? state : null;

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
              verified. GapSense will not invent curriculum choices or generate unsupported
              material. The next step unlocks as reviewed evidence becomes available.
            </p>
          </div>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => {
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
