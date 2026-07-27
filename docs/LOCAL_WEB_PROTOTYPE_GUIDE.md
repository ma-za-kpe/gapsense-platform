# Local web prototype guide

The current product is a local, web-first prototype. It does not require an account,
phone number, hosted AI key, WhatsApp, or deployment.

## Start it

```powershell
docker compose up -d --build --wait web frontend
```

Open [http://localhost:3000/](http://localhost:3000/).

Use the header appearance control to choose **Light**, **Dark**, or **System**. The system setting
follows the device preference, and the browser stores only this non-sensitive appearance choice.

## Use the first workflow

1. Choose a role: teacher, caregiver, learner, or tutor.
2. Choose the illustrative Ghana or Uganda sample context.
3. Choose the available **Practice activity** purpose. The future diagnostic and assessment-plan
   options remain visibly locked.
4. Review the anonymous choice and open the sample activity.
5. Use the separate learner worksheet and answer guidance.
6. Print, download, share, or copy the clearly labelled sample.

The starter bank is deterministic prototype content. It is deliberately labelled as a local
sample and is not presented as an official examination while curriculum evidence is reviewed.
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
hosted authentication, hosted AI, real learner data, and expansion beyond ADR-003's anonymous,
read-only `gapsense.org` surface remain on hold.
