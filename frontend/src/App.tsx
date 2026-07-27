import { useCallback, useEffect, useRef, useState } from "react";

import { browserAnalytics, type Analytics } from "./analytics/client";
import { AssessmentPlanner } from "./components/AssessmentPlanner";
import { AssessmentWorkspace } from "./components/AssessmentWorkspace";
import { BrandMark } from "./components/BrandMark";
import { CoveragePanels } from "./components/CoveragePanels";
import { CurriculumExplorer } from "./components/CurriculumExplorer";
import { ReadinessBanner } from "./components/ReadinessBanner";
import { useCoverage } from "./hooks/useCoverage";
import { useReadiness } from "./hooks/useReadiness";
import "./styles.css";

type AppProps = {
  readonly analytics?: Analytics;
};

type RouteMetadata = {
  readonly title: string;
  readonly description: string;
};

const routeMetadata = (path: string): RouteMetadata => {
  switch (path) {
    case "/":
      return {
        title: "GapSense — Evidence and honest activity samples",
        description:
          "Inspect public curriculum evidence for Ghana and Uganda, then try a clearly labelled illustrative activity sample.",
      };
    case "/curriculum":
      return {
        title: "Curriculum evidence — GapSense",
        description:
          "Inspect the public curriculum evidence boundary, including available subjects and missing records.",
      };
    case "/assessment":
      return {
        title: "Activity sample — GapSense",
        description:
          "Use, print, or download a clearly labelled GapSense illustrative activity sample.",
      };
    case "/about":
      return {
        title: "Trust and evidence — GapSense",
        description:
          "Read how GapSense handles evidence, review, saved choices, privacy, accessibility, and corrections.",
      };
    default:
      return {
        title: "Page not available — GapSense",
        description: "Return to GapSense public evidence and illustrative activity samples.",
      };
  }
};

const normalizePath = (path: string): string =>
  path.length > 1 && path.endsWith("/") ? path.slice(0, -1) : path;

function Header(): React.JSX.Element {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <a className="brand-link" href="/" aria-label="GapSense home">
          <BrandMark />
        </a>
        <nav className="desktop-nav" aria-label="Primary navigation">
          <a href="/#countries">Coverage</a>
          <a href="/curriculum">Curriculum</a>
          <a href="/about">About</a>
          <a className="button button--compact" href="/#planner">
            Try a sample
          </a>
        </nav>
        <details className="mobile-nav">
          <summary>Menu</summary>
          <nav aria-label="Mobile navigation">
            <a href="/#countries">Coverage</a>
            <a href="/curriculum">Curriculum</a>
            <a href="/about">About</a>
            <a href="/#planner">Try a sample</a>
          </nav>
        </details>
      </div>
    </header>
  );
}

function HomePage({
  analytics,
  onOpenAssessment,
  readiness,
  coverage,
}: {
  readonly analytics: Analytics;
  readonly onOpenAssessment: () => void;
  readonly readiness: ReturnType<typeof useReadiness>;
  readonly coverage: ReturnType<typeof useCoverage>;
}): React.JSX.Element {
  return (
    <>
      <section className="hero" id="top" aria-labelledby="hero-title">
        <div className="hero__inner section-shell">
          <div className="hero__copy">
            <span className="eyebrow">Public evidence · private sample choices</span>
            <h1 id="hero-title">See the evidence. Try an honest sample.</h1>
            <p className="hero__lead">
              Inspect current Ghana and Uganda coverage, then preview a clearly labelled activity.
              Missing curriculum evidence stays missing; a sample never becomes a diagnosis.
            </p>
            <div className="hero__actions">
              <a className="button button--primary" href="#planner">
                Try a sample activity
              </a>
              <a className="quiet-link" href="/curriculum">
                Inspect curriculum evidence
              </a>
            </div>
            <p className="hero__privacy">
              No account, name, school, or learner response is requested.
            </p>
          </div>
          <aside className="hero-evidence" aria-label="Current GapSense capability boundary">
            <span className="eyebrow">What is available now</span>
            <dl>
              <div>
                <dt>Country coverage</dt>
                <dd>Presence records available</dd>
              </div>
              <div>
                <dt>Illustrative activity</dt>
                <dd>Two clearly labelled samples</dd>
              </div>
              <div>
                <dt>Diagnosis</dt>
                <dd>Not available</dd>
              </div>
            </dl>
            <p>
              Country and authority names provide context. They do not imply official endorsement,
              alignment, or educator review.
            </p>
          </aside>
        </div>
      </section>

      <div className="readiness-shell section-shell">
        <ReadinessBanner
          status={readiness.status}
          onRetry={() => {
            analytics.track("readiness_retry_selected");
            readiness.retry();
          }}
        />
      </div>

      <AssessmentPlanner analytics={analytics} onOpenAssessment={onOpenAssessment} />

      <section className="countries section-shell" id="countries" aria-labelledby="countries-title">
        <div className="section-heading section-heading--split">
          <div>
            <span className="eyebrow">Public coverage catalogue</span>
            <h2 id="countries-title">Evidence presence, without inflated claims.</h2>
          </div>
          <div>
            <p>
              File presence, extraction, and human review are separate states. Unsupported
              level-and-subject combinations remain visibly unavailable.
            </p>
            <a className="quiet-link" href="/curriculum">
              Open the curriculum explorer
            </a>
          </div>
        </div>
        <CoveragePanels
          state={coverage.state}
          onRetry={() => {
            analytics.track("coverage_retry_selected");
            coverage.retry();
          }}
        />
      </section>
    </>
  );
}

function CurriculumPage({
  coverage,
}: {
  readonly coverage: ReturnType<typeof useCoverage>;
}): React.JSX.Element {
  return (
    <section className="page-shell section-shell" aria-labelledby="curriculum-page-title">
      <span className="eyebrow">Curriculum evidence explorer</span>
      <h1 id="curriculum-page-title">Inspect the public evidence boundary.</h1>
      <p className="page-lead">
        Browse only subject evidence currently exposed by the public catalogue. A missing record is
        a publication boundary, not permission to infer a curriculum claim.
      </p>
      <CurriculumExplorer state={coverage.state} onRetry={coverage.retry} />
    </section>
  );
}

function AboutPage(): React.JSX.Element {
  return (
    <section className="page-shell trust-page section-shell" aria-labelledby="about-title">
      <span className="eyebrow">Trust centre</span>
      <h1 id="about-title">How GapSense earns trust.</h1>
      <p className="page-lead">
        Claims stay smaller than the evidence. This public experience separates repository presence,
        extraction, human review, and illustrative product samples.
      </p>
      <div className="trust-grid">
        <article id="evidence">
          <h2>Evidence and review</h2>
          <p>
            The public catalogue reports only records returned by the GapSense evidence API.
            Presence does not mean alignment, approval, or educator review. Human-reviewed
            curriculum activities are not available yet.
          </p>
        </article>
        <article id="privacy">
          <h2>Privacy and saved choices</h2>
          <p>
            The sample asks for a role and country context only. Those choices are saved in this
            browser so the activity can reopen; no account, name, school, learner identity, or
            answer is collected by this flow. Clearing the sample removes the saved choice.
          </p>
        </article>
        <article id="accessibility">
          <h2>Accessibility commitment</h2>
          <p>
            GapSense supports keyboard navigation, visible focus, reduced motion, readable text,
            semantic landmarks, printable activities, and compact layouts. Report a barrier and
            include the device, browser, and page when possible.
          </p>
        </article>
        <article id="feedback">
          <h2>Feedback and correction</h2>
          <p>
            Evidence gaps and accessibility problems should be visible and correctable. Report an
            issue publicly without including learner or school personal information.
          </p>
          <a
            className="quiet-link"
            href="https://github.com/ma-za-kpe/gapsense-platform/issues/new"
            target="_blank"
            rel="noreferrer"
          >
            Report a correction or barrier
          </a>
        </article>
      </div>
    </section>
  );
}

function NotFoundPage(): React.JSX.Element {
  return (
    <section className="page-shell section-shell" aria-labelledby="not-found-title">
      <span className="eyebrow">404</span>
      <h1 id="not-found-title">This page is not available</h1>
      <p className="page-lead">
        The address may have changed, or the requested public page does not exist.
      </p>
      <a className="button button--primary" href="/">
        Return to GapSense
      </a>
    </section>
  );
}

function Footer(): React.JSX.Element {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner section-shell">
        <div>
          <BrandMark />
          <p>
            Built by{" "}
            <a
              className="attribution-link"
              href="https://startuptribunal.com/maku"
              target="_blank"
              rel="noreferrer"
            >
              Maku
            </a>{" "}
            for Africa. Not an official curriculum authority or examination provider.
          </p>
        </div>
        <nav aria-label="Trust links">
          <a href="/about">About</a>
          <a href="/about#privacy">Privacy</a>
          <a href="/about#accessibility">Accessibility</a>
          <a href="/about#feedback">Feedback</a>
        </nav>
        <a
          className="release-link"
          href="https://github.com/ma-za-kpe/gapsense-platform/releases"
          target="_blank"
          rel="noreferrer"
        >
          Releases
        </a>
      </div>
    </footer>
  );
}

export function App({ analytics = browserAnalytics }: AppProps): React.JSX.Element {
  const readiness = useReadiness();
  const coverage = useCoverage();
  const entryRecorded = useRef(false);
  const [path, setPath] = useState(() => normalizePath(window.location.pathname));

  const navigate = useCallback((destination: string) => {
    window.history.pushState({}, "", destination);
    setPath(normalizePath(window.location.pathname));
  }, []);

  useEffect(() => {
    const handlePopState = () => setPath(normalizePath(window.location.pathname));
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    const metadata = routeMetadata(path);
    document.title = metadata.title;
    let description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (description === null) {
      description = document.createElement("meta");
      description.name = "description";
      document.head.append(description);
    }
    description.content = metadata.description;
  }, [path]);

  useEffect(() => {
    if (entryRecorded.current) return;
    entryRecorded.current = true;
    analytics.track("entry_viewed");
  }, [analytics]);

  let page: React.JSX.Element;
  switch (path) {
    case "/":
      page = (
        <HomePage
          analytics={analytics}
          onOpenAssessment={() => navigate("/assessment")}
          readiness={readiness}
          coverage={coverage}
        />
      );
      break;
    case "/curriculum":
      page = <CurriculumPage coverage={coverage} />;
      break;
    case "/assessment":
      page = <AssessmentWorkspace onReturnHome={() => navigate("/#planner")} />;
      break;
    case "/about":
      page = <AboutPage />;
      break;
    default:
      page = <NotFoundPage />;
  }

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <Header />
      <main id="main-content">{page}</main>
      <Footer />
    </>
  );
}
