import { useState } from "react";

import { buildAssessmentDocument } from "../domain/assessmentDocument";
import { buildSampleActivity } from "../domain/sampleActivity";
import { clearSampleDraft, type DraftStorage, readSampleDraft } from "../domain/sampleDraft";

type AssessmentWorkspaceProps = {
  readonly onReturnHome: () => void;
  readonly storage?: DraftStorage;
};

type ActionState =
  | { readonly kind: "idle"; readonly message: "" }
  | { readonly kind: "success"; readonly message: string }
  | { readonly kind: "error"; readonly message: string };

const idleAction: ActionState = { kind: "idle", message: "" };

export function AssessmentWorkspace({
  onReturnHome,
  storage = window.localStorage,
}: AssessmentWorkspaceProps): React.JSX.Element {
  const [stored] = useState(() => readSampleDraft(storage));
  const [actionState, setActionState] = useState<ActionState>(idleAction);
  const draft = stored.recovery === "restored" ? stored.draft : null;
  const activity =
    draft?.reviewed === true && draft.role !== null && draft.country !== null
      ? buildSampleActivity(draft.role, draft.country)
      : null;

  if (activity === null) {
    return (
      <section className="workspace-empty section-shell" aria-labelledby="workspace-empty-title">
        <span className="eyebrow">Sample activity</span>
        <h1 id="workspace-empty-title">No saved sample activity</h1>
        <p>
          Choose a role and one illustrative country context first. No learner identity or response
          is needed.
        </p>
        <button className="button button--primary" type="button" onClick={onReturnHome}>
          Choose a sample
        </button>
      </section>
    );
  }

  const shareSummary = `GapSense ${activity.title}. ${activity.provenance}`;

  return (
    <section className="assessment-workspace section-shell" aria-labelledby="assessment-title">
      <div className="workspace-heading">
        <div>
          <span className="eyebrow">Illustrative sample · not official curriculum</span>
          <h1 id="assessment-title">{activity.title}</h1>
          <p>{activity.roleGuidance}</p>
        </div>
        <button
          className="button button--secondary"
          type="button"
          onClick={() => {
            clearSampleDraft(storage);
            onReturnHome();
          }}
        >
          Choose another sample
        </button>
      </div>

      <aside className="evidence-boundary evidence-boundary--strong" aria-label="Evidence boundary">
        <strong>What this is</strong>
        <span>{activity.provenance}</span>
        <span>
          Country and authority provide context only; they do not imply endorsement or alignment.
        </span>
      </aside>

      <article className="starter-activity starter-activity--workspace">
        <div className="starter-activity__header">
          <div>
            <span className="eyebrow">
              {activity.country} · {activity.level}
            </span>
            <h2>{activity.subject} activity sample</h2>
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
                const document = buildAssessmentDocument({
                  title: activity.title,
                  country: activity.country,
                  authority: activity.authority,
                  level: activity.level,
                  subject: activity.subject,
                  questions: activity.questions,
                  answers: activity.answers,
                });
                const blob = new Blob([document], { type: "text/html" });
                const url = URL.createObjectURL(blob);
                const link = window.document.createElement("a");
                link.href = url;
                link.download = "gapsense-sample-activity.html";
                link.click();
                URL.revokeObjectURL(url);
              }}
            >
              Download HTML
            </button>
            <button
              className="button button--secondary"
              type="button"
              onClick={() => {
                if (typeof navigator.share !== "function") {
                  setActionState({
                    kind: "error",
                    message:
                      "Sharing is unavailable. Copy the summary or download the activity instead.",
                  });
                  return;
                }
                void navigator
                  .share({ title: activity.title, text: shareSummary })
                  .then(() => setActionState({ kind: "success", message: "Share sheet opened." }))
                  .catch(() =>
                    setActionState({
                      kind: "error",
                      message: "Sharing did not finish. Download the activity instead.",
                    }),
                  );
              }}
            >
              Share
            </button>
            <button
              className="button button--secondary"
              type="button"
              onClick={() => {
                const clipboard = Reflect.get(navigator, "clipboard") as
                  { readonly writeText?: (text: string) => Promise<void> } | undefined;
                if (typeof clipboard?.writeText !== "function") {
                  setActionState({
                    kind: "error",
                    message: "Copying is unavailable. Download the activity instead.",
                  });
                  return;
                }
                void clipboard
                  .writeText(shareSummary)
                  .then(() => setActionState({ kind: "success", message: "Summary copied." }))
                  .catch(() =>
                    setActionState({
                      kind: "error",
                      message: "Copying is unavailable. Download the activity instead.",
                    }),
                  );
              }}
            >
              Copy summary
            </button>
          </div>
        </div>

        {actionState.kind === "idle" ? null : (
          <p role={actionState.kind === "error" ? "alert" : "status"}>{actionState.message}</p>
        )}

        <ol>
          {activity.questions.map((question) => (
            <li key={question}>
              <span>{question}</span>
              <span className="answer-line" />
            </li>
          ))}
        </ol>
        <details>
          <summary>Show answer guidance</summary>
          <ol>
            {activity.answers.map((answer) => (
              <li key={answer}>{answer}</li>
            ))}
          </ol>
        </details>
        <p className="starter-activity__note">{activity.provenance}</p>
      </article>
    </section>
  );
}
