import { describe, expect, it } from "vitest";

import {
  buildRobotsText,
  buildSearchScriptSource,
  buildSitemapXml,
  injectSearchHead,
  renderSearchHead,
  resolveSearchPublication,
} from "./publication";

describe("search publication contract", () => {
  it("defaults every unapproved mode to the deployment hold", () => {
    const publication = resolveSearchPublication(undefined, undefined);

    expect(publication).toEqual({ mode: "hold" });
    expect(resolveSearchPublication("preview", "https://example.test")).toEqual({
      mode: "hold",
    });
    expect(renderSearchHead(publication)).toContain(
      '<meta name="robots" content="noindex, nofollow, noarchive" />',
    );
    expect(renderSearchHead(publication)).not.toMatch(/canonical|application\/ld\+json|og:url/);
    expect(buildRobotsText(publication)).toBe("User-agent: *\nDisallow: /\n");
    expect(buildSitemapXml(publication)).toBeNull();
    expect(
      buildSearchScriptSource(publication, () => {
        throw new Error("hold mode must not hash structured data");
      }),
    ).toBe("");
  });

  it("builds one truthful canonical, sitemap, and WebSite graph for an approved origin", () => {
    const publication = resolveSearchPublication("public", "https://learn.gapsense.test/");
    const head = renderSearchHead(publication);
    const structuredData = /<script type="application\/ld\+json">(.+)<\/script>/.exec(head)?.[1];
    let valueGivenToHasher = "";

    expect(publication).toEqual({
      mode: "public",
      origin: "https://learn.gapsense.test",
    });
    expect(head).toContain('<link rel="canonical" href="https://learn.gapsense.test/" />');
    expect(head).toContain('<meta property="og:url" content="https://learn.gapsense.test/" />');
    expect(structuredData).toBeDefined();
    expect(JSON.parse(structuredData ?? "{}")).toEqual({
      "@context": "https://schema.org",
      "@type": "WebSite",
      description:
        "GapSense helps Ghanaian and Ugandan learning communities plan curriculum-aligned assessments and find the next useful learning step.",
      inLanguage: "en",
      name: "GapSense",
      url: "https://learn.gapsense.test/",
    });
    expect(buildRobotsText(publication)).toBe(
      "User-agent: *\nAllow: /\nSitemap: https://learn.gapsense.test/sitemap.xml\n",
    );
    expect(buildSitemapXml(publication)).toBe(
      '<?xml version="1.0" encoding="UTF-8"?>\n' +
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "  <url>\n" +
        "    <loc>https://learn.gapsense.test/</loc>\n" +
        "  </url>\n" +
        "</urlset>\n",
    );
    expect(
      buildSearchScriptSource(publication, (value) => {
        valueGivenToHasher = value;
        return "reviewed-base64-digest";
      }),
    ).toBe("'sha256-reviewed-base64-digest'");
    expect(valueGivenToHasher).toBe(structuredData);
  });

  it.each([
    [undefined, "requires an approved HTTPS origin"],
    ["not a URL", "valid absolute URL"],
    ["http://gapsense.test", "must use HTTPS"],
    // pragma: allowlist nextline secret -- synthetic URL proves public metadata rejects credentials
    ["https://user:pass@gapsense.test", "must not contain credentials"],
    ["https://gapsense.test/path", "must use the origin root"],
    ["https://gapsense.test/?campaign=1", "must not contain a query or fragment"],
    ["https://gapsense.test/#top", "must not contain a query or fragment"],
    ["https://localhost", "must not use a local host"],
    ["https://localhost.", "must not use a local host"],
    ["https://preview.localhost.", "must not use a local host"],
    ["https://127.0.0.1", "must not use a local host"],
    ["https://127.0.0.2", "must not use a local host"],
    ["https://0.0.0.0", "must not use a local host"],
    ["https://[::]", "must not use a local host"],
  ])("rejects unsafe public origin %s", (origin, message) => {
    expect(() => resolveSearchPublication("public", origin)).toThrow(message);
  });

  it("injects exactly one generated head into the reviewed template marker", () => {
    const template = "<head><!-- gapsense:search-head --></head>";
    const publication = resolveSearchPublication(undefined, undefined);

    expect(injectSearchHead(template, publication)).toBe(
      `<head>${renderSearchHead(publication)}</head>`,
    );
    expect(() => injectSearchHead("<head></head>", publication)).toThrow(
      "exactly one search-head marker",
    );
    expect(() =>
      injectSearchHead("<!-- gapsense:search-head --><!-- gapsense:search-head -->", publication),
    ).toThrow("exactly one search-head marker");
  });
});
