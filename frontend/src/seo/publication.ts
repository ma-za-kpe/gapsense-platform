export type SearchPublication =
  { readonly mode: "hold" } | { readonly mode: "public"; readonly origin: string };

const searchHeadMarker = "<!-- gapsense:search-head -->";
const siteName = "GapSense";
const title = "GapSense — Find the next learning step";
const description =
  "GapSense helps Ghanaian and Ugandan learning communities plan curriculum-aligned assessments and find the next useful learning step.";

function localHostname(hostname: string): boolean {
  const normalized = hostname.toLowerCase().replace(/\.+$/u, "");
  const unwrappedIpv6 =
    normalized.startsWith("[") && normalized.endsWith("]") ? normalized.slice(1, -1) : normalized;
  return (
    normalized === "localhost" ||
    normalized.endsWith(".localhost") ||
    normalized === "0.0.0.0" ||
    /^127(?:\.\d{1,3}){3}$/u.test(normalized) ||
    unwrappedIpv6 === "::" ||
    unwrappedIpv6 === "::1"
  );
}

export function resolveSearchPublication(
  mode: string | undefined,
  publicOrigin: string | undefined,
): SearchPublication {
  if (mode !== "public") {
    return { mode: "hold" };
  }
  if (publicOrigin === undefined || publicOrigin.trim() === "") {
    throw new Error("Public search publication requires an approved HTTPS origin");
  }

  let url: URL;
  try {
    url = new URL(publicOrigin);
  } catch {
    throw new Error("Public search publication requires a valid absolute URL");
  }
  if (url.protocol !== "https:") {
    throw new Error("Public search publication must use HTTPS");
  }
  if (url.username !== "" || url.password !== "") {
    throw new Error("Public search publication must not contain credentials");
  }
  if (url.pathname !== "/") {
    throw new Error("Public search publication must use the origin root");
  }
  if (url.search !== "" || url.hash !== "") {
    throw new Error("Public search publication must not contain a query or fragment");
  }
  if (localHostname(url.hostname)) {
    throw new Error("Public search publication must not use a local host");
  }

  return { mode: "public", origin: url.origin };
}

function canonicalUrl(publication: Extract<SearchPublication, { mode: "public" }>): string {
  return `${publication.origin}/`;
}

function structuredDataJson(publication: Extract<SearchPublication, { mode: "public" }>): string {
  return JSON.stringify({
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: siteName,
    description,
    url: canonicalUrl(publication),
    inLanguage: "en",
  });
}

export function renderSearchHead(publication: SearchPublication): string {
  const common = [
    `<title>${title}</title>`,
    `<meta name="description" content="${description}" />`,
    `<meta name="application-name" content="${siteName}" />`,
    '<meta property="og:type" content="website" />',
    `<meta property="og:site_name" content="${siteName}" />`,
    `<meta property="og:title" content="${title}" />`,
    `<meta property="og:description" content="${description}" />`,
    '<meta property="og:locale" content="en_GB" />',
    '<meta name="twitter:card" content="summary" />',
    `<meta name="twitter:title" content="${title}" />`,
    `<meta name="twitter:description" content="${description}" />`,
  ];
  if (publication.mode === "hold") {
    return [...common, '<meta name="robots" content="noindex, nofollow, noarchive" />'].join(
      "\n    ",
    );
  }

  const canonical = canonicalUrl(publication);
  return [
    ...common,
    '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />',
    `<link rel="canonical" href="${canonical}" />`,
    `<meta property="og:url" content="${canonical}" />`,
    `<script type="application/ld+json">${structuredDataJson(publication)}</script>`,
  ].join("\n    ");
}

export function injectSearchHead(template: string, publication: SearchPublication): string {
  const markerCount = template.split(searchHeadMarker).length - 1;
  if (markerCount !== 1) {
    throw new Error("GapSense index template must contain exactly one search-head marker");
  }
  return template.replace(searchHeadMarker, renderSearchHead(publication));
}

export function buildRobotsText(publication: SearchPublication): string {
  if (publication.mode === "hold") {
    return "User-agent: *\nDisallow: /\n";
  }
  return `User-agent: *\nAllow: /\nSitemap: ${publication.origin}/sitemap.xml\n`;
}

export function buildSitemapXml(publication: SearchPublication): string | null {
  if (publication.mode === "hold") {
    return null;
  }
  return (
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    "  <url>\n" +
    `    <loc>${canonicalUrl(publication)}</loc>\n` +
    "  </url>\n" +
    "</urlset>\n"
  );
}

export function buildSearchScriptSource(
  publication: SearchPublication,
  digestBase64: (value: string) => string,
): string {
  if (publication.mode === "hold") {
    return "";
  }
  const digest = digestBase64(structuredDataJson(publication));
  return `'sha256-${digest}'`;
}
