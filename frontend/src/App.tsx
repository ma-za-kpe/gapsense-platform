import { useEffect, useRef } from "react";

import { browserAnalytics, type Analytics } from "./analytics/client";
import { AssessmentPlanner } from "./components/AssessmentPlanner";
import { BrandMark } from "./components/BrandMark";
import { CoveragePanels } from "./components/CoveragePanels";
import { ReadinessBanner } from "./components/ReadinessBanner";
import { useCoverage } from "./hooks/useCoverage";
import { useReadiness } from "./hooks/useReadiness";
import "./styles.css";

type AppProps = {
  readonly analytics?: Analytics;
};

export function App({ analytics = browserAnalytics }: AppProps): React.JSX.Element {
  const readiness = useReadiness();
  const coverage = useCoverage();
  const entryRecorded = useRef(false);

  useEffect(() => {
    if (entryRecorded.current) {
      return;
    }
    entryRecorded.current = true;
    analytics.track("entry_viewed");
  }, [analytics]);

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <header className="site-header">
        <div className="site-header__inner">
          <a className="brand-link" href="#top" aria-label="GapSense home">
            <BrandMark />
          </a>
          <nav aria-label="Primary navigation">
            <a
              href="#countries"
              onClick={() => {
                analytics.track("navigation_countries_selected");
              }}
            >
              Countries
            </a>
            <a
              href="#principles"
              onClick={() => {
                analytics.track("navigation_principles_selected");
              }}
            >
              Why GapSense
            </a>
            <a
              className="button button--compact"
              href="#planner"
              onClick={() => {
                analytics.track("navigation_planner_selected");
              }}
            >
              Start free
            </a>
          </nav>
        </div>
      </header>

      <main id="main-content">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero__wash" aria-hidden="true" />
          <div className="hero__inner section-shell">
            <div className="hero__copy">
              <div className="hero__kicker reveal reveal--one">
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
              <h1 id="hero-title" className="reveal reveal--two">
                Find the next <span>learning step.</span>
              </h1>
              <p className="hero__lead reveal reveal--three">
                Plan focused practice and curriculum-aligned assessment with evidence you can see,
                language that protects learner dignity, and no personal data required.
              </p>
              <div className="hero__actions reveal reveal--four">
                <a
                  className="button button--primary button--large"
                  href="#planner"
                  onClick={() => {
                    analytics.track("navigation_planner_selected");
                  }}
                >
                  Plan a free assessment <span aria-hidden="true">→</span>
                </a>
                <a
                  className="quiet-link"
                  href="#countries"
                  onClick={() => {
                    analytics.track("navigation_countries_selected");
                  }}
                >
                  Explore country coverage
                </a>
              </div>
              <p className="hero__privacy reveal reveal--four">
                No account. No learner data. No hidden AI dependency.
              </p>
            </div>

            <div className="hero-visual reveal reveal--three" aria-hidden="true">
              <div className="map-card">
                <div className="map-card__header">
                  <span>Learning path</span>
                  <span className="map-card__live">Evidence linked</span>
                </div>
                <div className="learning-map">
                  <svg viewBox="0 0 520 330" role="presentation">
                    <path className="map-line map-line--one" d="M90 245C150 245 148 170 215 170" />
                    <path className="map-line map-line--two" d="M250 170C322 170 315 85 400 85" />
                    <path
                      className="map-line map-line--three"
                      d="M250 170C322 170 320 250 420 250"
                    />
                  </svg>
                  <div className="map-node map-node--start">
                    <span>Observed</span>
                    <strong>Fractions</strong>
                  </div>
                  <div className="map-node map-node--root">
                    <span>Earliest gap</span>
                    <strong>Equal groups</strong>
                    <small>Start here</small>
                  </div>
                  <div className="map-node map-node--upper">
                    <span>Prerequisite</span>
                    <strong>Counting</strong>
                  </div>
                  <div className="map-node map-node--next">
                    <span>Next step</span>
                    <strong>Visual practice</strong>
                  </div>
                </div>
                <div className="map-card__footer">
                  <span className="confidence-ring">92</span>
                  <div>
                    <strong>Reasoning stays visible</strong>
                    <span>Sources, confidence, and uncertainty travel together.</span>
                  </div>
                </div>
              </div>
              <div className="floating-note floating-note--ghana">
                <span>GH</span>
                <div>
                  <strong>Ghana</strong>
                  <small>NaCCA structure</small>
                </div>
              </div>
              <div className="floating-note floating-note--uganda">
                <span>UG</span>
                <div>
                  <strong>Uganda</strong>
                  <small>NCDC structure</small>
                </div>
              </div>
            </div>
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

        <AssessmentPlanner analytics={analytics} />

        <section
          className="countries section-shell"
          id="countries"
          aria-labelledby="countries-title"
        >
          <div className="section-heading section-heading--split">
            <div>
              <span className="eyebrow">Country truth first</span>
              <h2 id="countries-title">One platform. Two distinct education systems.</h2>
            </div>
            <p>
              We preserve each authority’s terminology and curriculum structure. Coverage is only
              called ready after source, structure, automated checks, and expert review agree.
            </p>
          </div>

          <CoveragePanels
            state={coverage.state}
            onRetry={() => {
              analytics.track("coverage_retry_selected");
              coverage.retry();
            }}
          />
        </section>

        <section className="principles" id="principles" aria-labelledby="principles-title">
          <div className="section-shell">
            <div className="section-heading section-heading--centered">
              <span className="eyebrow eyebrow--light">A calmer kind of education technology</span>
              <h2 id="principles-title">Useful before it is impressive.</h2>
              <p>Every product decision has to earn trust in a real classroom or home.</p>
            </div>
            <div className="principle-grid">
              <article>
                <span className="principle-number">01</span>
                <h3>Free means complete</h3>
                <p>A usable learner activity and educator guide—not a teaser behind a paywall.</p>
              </article>
              <article>
                <span className="principle-number">02</span>
                <h3>Evidence stays visible</h3>
                <p>Curriculum versions, sources, reasoning, review state, and uncertainty.</p>
              </article>
              <article>
                <span className="principle-number">03</span>
                <h3>AI stays optional</h3>
                <p>Deterministic planning works locally even when Ollama is unavailable.</p>
              </article>
              <article>
                <span className="principle-number">04</span>
                <h3>Low bandwidth is premium UX</h3>
                <p>Fast, resumable, printable, keyboard-ready, and clear on a small screen.</p>
              </article>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="section-shell site-footer__inner">
          <BrandMark />
          <p>
            <strong>
              Built by{" "}
              <a
                className="attribution-link"
                href="https://startuptribunal.com/maku"
                target="_blank"
                rel="noreferrer"
              >
                Maku
              </a>{" "}
              for Africa.
            </strong>{" "}
            Not an official examination provider.
          </p>
          <a href="#top">Back to top ↑</a>
          <a
            className="release-link"
            href="https://github.com/ma-za-kpe/gapsense-platform/releases"
            target="_blank"
            rel="noreferrer"
          >
            Latest version <span aria-hidden="true">↗</span>
          </a>
        </div>
      </footer>
    </>
  );
}
