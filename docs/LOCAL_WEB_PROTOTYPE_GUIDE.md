# Local web prototype guide

The current product is a local, web-first prototype. It does not require an account,
phone number, hosted AI key, WhatsApp, or deployment.

## Start it

```powershell
docker compose up -d --build --wait web frontend
```

Open [http://localhost:3000/](http://localhost:3000/).

## Use the first workflow

1. Choose a role: teacher, caregiver, learner, or tutor.
2. Choose Ghana or Uganda.
3. Choose the purpose: practice, diagnostic check, or assessment plan.
4. Review the private local plan.
5. Choose an available level and subject.
6. Generate the five-question starter activity.
7. Open answer guidance or use **Print / save PDF**.

The starter bank is deterministic prototype content. It is deliberately labelled as a local
draft and is not presented as an official examination while curriculum evidence is reviewed.
Unsupported curriculum combinations remain out of scope rather than being invented.

## Validate it

Run the frontend checks in Docker:

```powershell
docker compose run --rm --no-deps frontend npm run validate
docker compose --profile test run --rm browser-tests
```

The browser target is required for Playwright because the normal development image intentionally
does not download browsers.

## What is next

The next product slice replaces the starter bank with versioned, educator-reviewed evidence,
starting with Ghana primary Mathematics and Uganda Primary 1–3 Mathematics. WhatsApp delivery,
hosted authentication, hosted AI, and production deployment remain on hold.
