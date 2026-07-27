import { useCallback, useEffect, useRef, useState } from "react";

import { browserAnalytics, type Analytics } from "./analytics/client";
import { AssessmentPlanner } from "./components/AssessmentPlanner";
import { AssessmentWorkspace } from "./components/AssessmentWorkspace";
import { BrandMark } from "./components/BrandMark";
import { CoveragePanels } from "./components/CoveragePanels";
import { CurriculumExplorer } from "./components/CurriculumExplorer";
import { ReadinessBanner } from "./components/ReadinessBanner";
import { ThemeSwitcher } from "./components/ThemeSwitcher";
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
        title: "GapSense — Find the next learning step",
        description:
          "See how GapSense connects observed difficulty, curriculum prerequisites, and practical next steps while keeping current evidence limits explicit.",
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
      <div className="site-header__inner section-shell">
        <a className="brand-link" href="/" aria-label="GapSense home">
          <BrandMark />
        </a>
        <div className="header-actions">
          <nav className="desktop-nav" aria-label="Primary navigation">
            <a href="/#countries">Coverage</a>
            <a href="/curriculum">Curriculum</a>
            <a href="/about">About</a>
            <a className="button button--compact" href="/#planner">
              Try a sample
            </a>
          </nav>
          <ThemeSwitcher />
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
            <div className="hero__kicker">
              <span className="status-orb" aria-hidden="true" />
              Built by{" "}
              <a
                className="attribution-link"
                href="https://startuptribunal.com/maku"
                target="_blank"
                rel="noreferrer"
              >
                Maku
              </a>{" "}
              for Africa, grounded first in Ghana and Uganda.
            </div>
            <h1 id="hero-title">
              Find the next <span>learning step.</span>
            </h1>
            <p className="hero__promise">Find the gap. See the reason. Take the next step.</p>
            <p className="hero__lead">
              GapSense is being built to help educators identify the earliest learning prerequisite
              that may be blocking progress, understand why it matters, and choose a practical next
              action—without reducing a learner to a score or deficit.
            </p>
            <p className="hero__boundary">
              Today, the public release offers clearly labelled activity samples and an inspectable
              Ghana and Uganda evidence catalogue. It does not diagnose a learner or claim reviewed
              curriculum alignment.
            </p>
            <div className="hero__actions">
              <a className="button button--primary button--large" href="#planner">
                Plan a sample activity <span aria-hidden="true">→</span>
              </a>
              <a className="quiet-link" href="/curriculum">
                Explore curriculum evidence
              </a>
            </div>
            <p className="hero__privacy">No account. No learner data. No hidden AI dependency.</p>
          </div>
          <figure
            className="hero-visual"
            aria-labelledby="learning-path-title"
            aria-describedby="learning-path-note"
          >
            <div className="map-card">
              <div className="map-card__header">
                <strong id="learning-path-title">Illustrative learning path</strong>
                <span className="map-card__model">Product model</span>
              </div>
              <div className="learning-map" role="list" aria-label="Example prerequisite path">
                <svg viewBox="0 0 520 330" aria-hidden="true" focusable="false">
                  <path className="map-line map-line--one" d="M90 245C150 245 148 170 215 170" />
                  <path className="map-line map-line--two" d="M250 170C322 170 315 85 400 85" />
                  <path className="map-line map-line--three" d="M250 170C322 170 320 250 420 250" />
                </svg>
                <div className="map-node map-node--start" role="listitem">
                  <span>Observed topic</span>
                  <strong>Fractions</strong>
                </div>
                <div className="map-node map-node--root" role="listitem">
                  <span>Earliest gap</span>
                  <strong>Equal groups</strong>
                  <small>Start here</small>
                </div>
                <div className="map-node map-node--upper" role="listitem">
                  <span>Foundation</span>
                  <strong>Counting</strong>
                </div>
                <div className="map-node map-node--next" role="listitem">
                  <span>Next action</span>
                  <strong>Visual grouping practice</strong>
                </div>
              </div>
              <div className="map-card__footer">
                <span className="reasoning-mark" aria-hidden="true">
                  ↳
                </span>
                <div>
                  <strong>Reasoning should stay visible</strong>
                  <span>Sources, review state, and uncertainty travel together.</span>
                </div>
              </div>
            </div>
            <figcaption className="learning-model-note" id="learning-path-note">
              Example only — not a learner diagnosis or a claim about current curriculum coverage.
            </figcaption>
            <div className="floating-note floating-note--ghana" aria-hidden="true">
              <span>GH</span>
              <div>
                <strong>Ghana</strong>
                <small>NaCCA structure</small>
              </div>
            </div>
            <div className="floating-note floating-note--uganda" aria-hidden="true">
              <span>UG</span>
              <div>
                <strong>Uganda</strong>
                <small>NCDC structure</small>
              </div>
            </div>
          </figure>
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
    <section
      className="page-shell page-shell--curriculum section-shell"
      aria-labelledby="curriculum-page-title"
    >
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
            The sample stores only the role, country context, and available purpose; the appearance
            control stores only your theme preference. These choices stay in this browser so the
            experience can reopen; no account, name, school, learner identity, or answer is
            collected by this flow. Clearing the sample removes its saved choice.
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
    <section
      className="page-shell page-shell--not-found section-shell"
      aria-labelledby="not-found-title"
    >
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
