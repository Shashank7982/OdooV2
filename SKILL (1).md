---
name: open-source-api-search
description: Discovers, verifies, evaluates, scores, ranks, and selects the best real Open Source APIs, OpenAPI/Swagger specifications, and SDKs for each target search engine, bot, API, or technology. Enforces zero-hallucination via live HTTP endpoint and spec verification (HTTP 200/404 gate). Selects Top 10 from 500+ candidates using a 100-point evidence-based scoring model. Does not perform relative multi-candidate ranking across different targets or edit external databases directly.
---

# Skill: Open Source API Discovery & Selection (`open-source-api-search`)

## 1. Skill Identity & Core Purpose

- **Skill Name**: `open-source-api-search`
- **Domain**: AI-Powered Technical Research System / Open Source API Discovery Engine
- **Primary Function**: Single-responsibility engine for discovering, verifying existence against live HTTP endpoints and OpenAPI/Swagger specs, evaluating across 10 weighted criteria, scoring on a 100-point model, deduplicating, ranking, and selecting the Top 10 highest-quality Open Source APIs for each target technology.

---

## 2. Pipeline Architecture

The skill follows this exact pipeline. No step may be skipped.

```text
Discover (multi-vector search across GitHub, OpenAPI catalogs, vendor portals)
   ↓
Verify (zero-hallucination gate: live HTTP GET/HEAD 200/404 on base URL & specs)
   ↓
Filter (remove synthetic, non-existent, broken, proprietary, or dead APIs)
   ↓
Evaluate (assess open-source status, endpoints, docs, tech stack, architecture)
   ↓
Score (compute 100-point composite score across 10 criteria)
   ↓
Deduplicate (endpoint, domain, and wrapper deduplication)
   ↓
Rank (sort by overall_score descending, classify into ranking bands)
   ↓
Select Top 10 (apply 9 mandatory verification gates & selection rules)
   ↓
Write to Excel (map 48 internal canonical fields → 9 Excel columns)
   ↓
Validate final records (schema validation + live HTTP verification gate)
```

### Scripts Mapping

| Pipeline Step | Script |
|:---|:---|
| Discover + Live HTTP Verify | `scripts/search_apis.py` |
| Validate Schema & Gates | `scripts/validate_apis.py` |
| Evaluate + Score + Rank | `scripts/score_apis.py` |
| Deduplicate | `scripts/deduplicate_apis.py` |
| Write to Excel | `scripts/write_open_source_apis.py` |

---

## 3. Zero-Hallucination Rule

> [!CAUTION]
> **MANDATORY RULE: Never invent an API, endpoint, OpenAPI spec, or URL.**

Every API must be a real, operational service or open-source codebase. For every candidate API, verify using live HTTP GET/HEAD requests against:

```text
1. Base URL / Endpoint (e.g. https://api.target.com/v1/)
2. OpenAPI Spec (e.g. https://api.target.com/openapi.json, /swagger.json)
3. Documentation URL / Developer Portal
4. GitHub / GitLab Source Repository
```

### Verification Status Codes

| HTTP Status | Action |
|:---|:---|
| `HTTP 200` + valid spec/docs | API proceeds to evaluation |
| `HTTP 404` / Unreachable | **IMMEDIATELY REJECT** |
| `HTTP 401/403` (auth required) | Accept if documentation is HTTP 200 reachable |
| Dead domain / Connection refused | Reject as `API_DEAD` |

---

## 4. Candidate Discovery Sources

Candidates are discovered from:
- GitHub & GitLab source repositories
- OpenAPI / Swagger catalogs & registries
- Official organization developer portals & API documentation
- Package registry SDKs (PyPI, npm, Maven Central, Crates.io)
- API directories & curated ecosystem lists

---

## 5. Target Understanding Model

Before searching for APIs, generate a structured target context:

```text
Target name            → Primary name (e.g. "DuckDuckGo")
Target type            → Search engine / bot / crawler / API gateway / platform
Organization/vendor    → Company or org behind the target
Aliases                → Alternative names, abbreviations, former names
Website/domain         → Official website
Relevant keywords      → Search queries (e.g. "duckduckgo search api", "searxng openapi")
```

Generate **multiple candidate search queries** to discover both official and open-source community APIs.

---

## 6. Open Source Verification Layer

Distinguish true open-source APIs from public/cloud APIs:

| Status | Criteria |
|:---|:---|
| `OPEN_SOURCE_CONFIRMED` | Backend source code available with an OSI-approved license (MIT, Apache-2.0, GPL) |
| `SOURCE_AVAILABLE_BUT_LICENSE_UNCLEAR` | Source available but non-standard license |
| `SDK_ONLY_OPEN_SOURCE` | Client SDK is open source, but API backend is a cloud service |
| `PUBLIC_API_NOT_OPEN_SOURCE` | Public HTTP API, backend source not published |
| `PROPRIETARY` | Closed-source commercial API |

> True open-source APIs (`OPEN_SOURCE_CONFIRMED`) receive maximum points in the open-source evaluation criterion.

---

## 7. 5-Tier Architecture Model

Every API is analyzed across 5 architectural tiers:

```text
Tier 1 — API Interface       → REST, GraphQL, gRPC, WebSocket, OpenAPI 3.0
Tier 2 — Application Layer   → FastAPI, Django, Flask, Express, Spring Boot, Go
Tier 3 — Data Layer          → PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch
Tier 4 — Infrastructure      → Docker, Docker Compose, Kubernetes, Helm
Tier 5 — External Deps       → Third-party APIs, OAuth providers, AI models
```

---

## 8. 100-Point Scoring System

| Criterion | Weight | Scoring Focus |
|:---|---:|:---|
| **Requirement Match** | 25 | Direct functional match for target engine/bot/tool |
| **API Functionality & Capabilities** | 15 | Endpoint coverage, search/query capabilities, response richness |
| **Open-Source Validity & License** | 10 | Confirmed open-source implementation + recognized SPDX license |
| **API Availability & Live Status** | 10 | HTTP 200 reachable endpoints, active server, SSL validity |
| **Documentation Quality** | 10 | Getting started guides, OpenAPI/Swagger spec, clear examples |
| **Maintenance & Activity** | 10 | Recent commits, releases, active issue handling, no archive flag |
| **Reliability & Infrastructure** | 5 | Response time, HTTPS security, low error rate |
| **Security & Authentication** | 5 | Standard auth (OAuth2, Bearer, API Key, No Auth), security policies |
| **SDK & Ecosystem Support** | 5 | Multi-language SDK support, package registry availability |
| **Architecture & Self-Hosting** | 5 | Docker / Compose / K8s support, clean 5-tier architecture |
| **Total** | **100** | |

### Mandatory Gates (applied after scoring)
1. `requirement_match >= 10/25` — REJECT if FAIL
2. `api_availability >= 5/10` — REJECT if FAIL
3. `evidence_http_status == 200` — REJECT if FAIL

### Ranking Bands
| Band | Score Range |
|:---|:---|
| Excellent | 90–100 |
| High | 80–89 |
| Good | 70–79 |
| Medium | 60–69 |
| Reject | <60 |

---

## 9. 9 Mandatory Verification Gates

1. *Gate 1 (Existence)*: API or project actually exists
2. *Gate 2 (Source)*: Accessible source repository or official portal
3. *Gate 3 (License)*: License or public terms of use documented
4. *Gate 4 (Implementation)*: Real API implementation or spec exists
5. *Gate 5 (Documentation)*: Reachable documentation or OpenAPI/Swagger spec
6. *Gate 6 (Specification)*: Valid OpenAPI/Swagger schema when specified
7. *Gate 7 (Accessibility)*: Base URL or spec URL is HTTP reachable
8. *Gate 8 (Maintenance)*: Not completely dead/abandoned
9. *Gate 9 (Requirement Match)*: Relevance score ≥ 10/25

---

## 10. 12 Hard Rejection Rules

| ID | Rule | Action |
|:---|:---|:---|
| R01 | API base URL and documentation both HTTP 404 / Unreachable | REJECT |
| R02 | API appears synthetic or fabricated | REJECT |
| R03 | API has no functional relevance to target | REJECT |
| R04 | Generic library without target-specific API integration | REJECT |
| R05 | Fully proprietary closed-source API without open spec | REJECT |
| R06 | GitHub repository exists but contains no API code | REJECT |
| R07 | SDK repository without underlying API or backend specs | REJECT |
| R08 | API is explicitly archived/abandoned with dead endpoints | REJECT |
| R09 | Duplicate of another selected API | REJECT |
| R10 | Severe security vulnerabilities or broken SSL | REJECT |
| R11 | Score below 60/100 threshold | REJECT |
| R12 | Failed mandatory requirement match gate | REJECT |

---

## 11. 48-Field Canonical Data Model

Every API record uses the 48-field schema defined in `resources/data_models.json`:

```json
{
  "api_name": "",
  "normalized_api_name": "",
  "api_description": "",
  "api_category": "",
  "api_type": "REST|GraphQL|WebSocket|gRPC|SOAP|RPC|Event/Webhook",
  "protocol": "",
  "source_repository_url": "",
  "official_website": "",
  "documentation_url": "",
  "openapi_url": "",
  "swagger_url": "",
  "graphql_url": "",
  "base_url": "",
  "license_spdx": "",
  "license_url": "",
  "open_source_status": "OPEN_SOURCE_CONFIRMED|...",
  "api_status": "API_LIVE|API_PARTIALLY_LIVE|...",
  "maintenance_status": "ACTIVE|MAINTAINED|...",
  "latest_version": "",
  "latest_release_date": "",
  "last_commit_date": "",
  "stars": 0,
  "forks": 0,
  "contributors": 0,
  "primary_language": "",
  "backend_framework": "",
  "database": "",
  "deployment": "",
  "self_hostable": true,
  "docker_support": true,
  "authentication_mechanism": "",
  "auth_complexity": "NONE|LOW|MEDIUM|HIGH",
  "rate_limit_summary": "",
  "pricing_model": "",
  "endpoint_count": 0,
  "sdk_languages": [],
  "official_sdks": [],
  "package_registries": [],
  "versioning_scheme": "",
  "documentation_score": 0,
  "maintenance_score": 0,
  "security_score": 0,
  "reliability_score": 0,
  "overall_score": 0,
  "confidence_score": "HIGH|MEDIUM|LOW",
  "verification_status": "",
  "evidence_http_status": 200,
  "last_verified_at": "",
  "selection_reason": "",
  "rejection_reason": ""
}
```

---

## 12. Excel Output Mapping

The 48 internal fields map to the 9-column Excel `Open Source APIs` sheet:

| Col | Header | Source |
|:---:|:---|:---|
| 1 | `S.No` | Sequential counter (1, 2, 3...) |
| 2 | `Search Engine Name` | `target_name` |
| 3 | `Category` | `category` |
| 4 | `API Name / Product` | `api_name` |
| 5 | `API Type / Protocol` | `api_type` + ' / ' + `protocol` |
| 6 | `Open Source / License` | `open_source_status` + ' (' + `license_spdx` + ')' |
| 7 | `Documentation / Spec URL` | `openapi_url` || `documentation_url` || `source_repository_url` |
| 8 | `Base URL / Endpoint` | `base_url` || `official_website` |
| 9 | `API Capabilities & Code Sample` | Key capabilities + verified `curl` / `Python` code snippet |

---

## 13. Scope Boundaries

This skill is strictly responsible for:
- Target context analysis & multi-query API discovery
- Live HTTP GET/HEAD verification (HTTP 200/404 gate)
- OpenAPI/Swagger spec parsing & endpoint extraction
- 48-field canonical record construction
- 100-point multi-criteria scoring & band classification
- Endpoint, domain, and wrapper deduplication
- Ranked Top 10 selection with mandatory gates
- Updating the Excel `Open Source APIs` sheet

## Explicit Non-Scope Declarations

This skill MUST NOT perform:
- ❌ GitHub repository discovery outside API contexts (delegated to `github-repository-search`)
- ❌ PyPI package discovery outside SDK contexts (delegated to `pypi-package-search`)
- ❌ YouTube video search (delegated to `youtube-tutorial-search`)
- ❌ Cross-target comparative ranking

---

## 14. Selection Philosophy

```text
Correctness > Requirement Match > Open-Source Validity > Live Reachability >
Documentation Quality > Maintenance > Architecture > Security > SDK Ecosystem
```

Never optimize for quantity alone. Return only verified, operational open-source APIs.
---

## 15. Deduplication Logic & Endpoint Normalization

- **Canonical Key Normalization**: Lowercase API name with hyphens (PEP 503 style).
- **Base URL & OpenAPI Spec Deduplication**: Group candidates by `base_url`, `openapi_url`, or `source_repository_url`.
- **Near-Duplicate Wrapper Detection**: Identify thin wrappers or mirrors of the same underlying API service. Keep candidate with highest `overall_score` and mark others as `REJECTED`.

---

## 16. Zero-Hallucination Validation Gate Rules

1. **48 Field Completeness**: All 48 fields must be populated.
2. **Live Reachability Gate**: `evidence_http_status` MUST be `200`. HTTP 404 or connection failure results in immediate rejection.
3. **Open-Source Status Classification**:
   - `OPEN_SOURCE_CONFIRMED`: Source code + OSI-approved license.
   - `PUBLIC_API_NOT_OPEN_SOURCE`: Public API, backend source not available.
   - `PROPRIETARY`: Closed-source commercial API (**REJECTED**).
4. **Conditional Rejection Reason**: If `pipeline_status` == `REJECTED`, `rejection_reason` MUST be non-empty string.

---

## 17. Excel Output Writer Specifications (9 Columns)

Maps 48 canonical fields to the 9-column `Open Source APIs` Excel sheet:

| Col | Header | Source Field / Formula |
|:---:|:---|:---|
| 1 | `S.No` | Sequential counter (1, 2, 3...) |
| 2 | `Search Engine Name` | `target_name` |
| 3 | `Category` | `category` |
| 4 | `API Name / Product` | `api_name` |
| 5 | `API Type / Protocol` | `api_type + ' / ' + protocol` |
| 6 | `Open Source / License` | `open_source_status + ' (' + license_spdx + ')'` |
| 7 | `Documentation / Spec URL` | `openapi_url` \|\| `documentation_url` \|\| `source_repository_url` |
| 8 | `Base URL / Endpoint` | `base_url` \|\| `official_website` |
| 9 | `API Capabilities & Code` | Synthesized capabilities + verified `curl` / `Python` integration code sample |

---

## 18. Canonical Example Objects (Valid vs. Invalid Patterns)

### A. Valid Candidate Example Pattern

```json
{
  "api_name": "SearXNG REST API",
  "normalized_api_name": "searxng-rest-api",
  "api_description": "Free and open-source privacy-respecting metasearch engine API.",
  "api_category": "Privacy Search Engine API",
  "api_type": "REST",
  "protocol": "REST / OpenAPI 3.0",
  "source_repository_url": "https://github.com/searxng/searxng",
  "official_website": "https://searx.space",
  "documentation_url": "https://docs.searxng.org/dev/search_api.html",
  "openapi_url": "https://docs.searxng.org/openapi.json",
  "swagger_url": null,
  "graphql_url": null,
  "base_url": "https://searxng.site/search",
  "license_spdx": "AGPL-3.0",
  "license_url": "https://github.com/searxng/searxng/blob/master/LICENSE",
  "open_source_status": "OPEN_SOURCE_CONFIRMED",
  "api_status": "API_LIVE",
  "maintenance_status": "ACTIVE",
  "latest_version": "2024.5.0",
  "latest_release_date": "2024-05-10",
  "last_commit_date": "2026-08-10",
  "stars": 12400,
  "forks": 1850,
  "contributors": 140,
  "primary_language": "Python",
  "backend_framework": "Flask",
  "database": "Redis",
  "deployment": "Docker Compose",
  "self_hostable": true,
  "docker_support": true,
  "authentication_mechanism": "None (Public API)",
  "auth_complexity": "NONE",
  "rate_limit_summary": "100 requests per minute",
  "pricing_model": "Free / Open Source",
  "endpoint_count": 5,
  "sdk_languages": ["Python", "JavaScript"],
  "official_sdks": ["searxng-py"],
  "package_registries": ["PyPI", "npm"],
  "versioning_scheme": "Calendar Versioning",
  "documentation_score": 9,
  "maintenance_score": 10,
  "security_score": 9,
  "reliability_score": 9,
  "overall_score": 92,
  "confidence_score": "HIGH",
  "verification_status": "VERIFIED_LIVE",
  "evidence_http_status": 200,
  "last_verified_at": "2026-08-17T05:00:00Z",
  "selection_reason": "Top open-source metasearch API with Docker self-hosting support.",
  "rejection_reason": null,
  "pipeline_status": "SELECTED"
}
```

### B. Common Invalid Patterns & Rejection Triggers

- **Proprietary API Without Open Spec**: `open_source_status: "PROPRIETARY"` -> **REJECTED**.
- **Unreachable Base URL & Docs**: `evidence_http_status: 404` -> **REJECTED**.
- **Missing Rejection Reason**: `pipeline_status: "REJECTED"` but `rejection_reason` is null -> **REJECTED**.
---

## 20. Canonical Schema Field Count Integrity & Fail-Fast Rule

- **Canonical Schema Count**: The `open-source-api-search` canonical data model contains **exactly 50 fields** (`api_name` through `rejection_reason` + provenance metadata).
- **CANONICAL SCHEMA RULE**: Schema field count MUST be programmatically validated before pipeline execution.
- **Fail-Fast Enforcement**: If declared field count != actual field count -> **`FAIL_FAST`**. The validator, scorer, and writer scripts must strictly agree on the 50-field schema.

---

## 21. API Deployment Classification

Open-source API projects MUST NOT be rejected merely because no public HTTP endpoint exists. Every API is classified into one of 5 deployment models:

1. **`HOSTED_PUBLIC_API`**: Public endpoint currently accessible on the internet.
2. **`SELF_HOSTED_API`**: Open-source implementation exists but no official public endpoint is operated.
3. **`HOSTED_AND_SELF_HOSTED`**: Both an official hosted public endpoint and self-hosting options (Docker / K8s) are available.
4. **`SPEC_ONLY`**: Valid OpenAPI/GraphQL/gRPC specification exists without a verified live endpoint.
5. **`DEAD_ARCHIVED`**: No usable implementation or deployment path available (**REJECTED**).

> **Status Mapping**:
> - `api_status = API_LIVE` (Hosted public API working)
> - `api_status = SELF_HOSTABLE_ONLY` (Open-source codebase with Docker/setup instructions, no public endpoint)
> - `api_status = SPEC_ONLY` (OpenAPI spec verified)
> - `api_status = API_DEAD` (Unreachable and unmaintainable)

---

## 22. Endpoint-Level Verification Engine (Endpoint-Aware Verification)

Never treat an HTTP 200 on a homepage as proof that the API works. Perform endpoint-level verification:

1. Verify base domain and documentation/spec endpoint.
2. Parse available OpenAPI/Swagger/GraphQL specification.
3. Select representative functional endpoints (e.g. `GET /v1/search`, `POST /v1/query`).
4. Test correct HTTP method for each representative endpoint.
5. Validate expected HTTP response class (`2xx`, `401/403` for auth-required, `429` for rate-limited).
6. Record latency and response status.

### Verification Status Taxonomy
- **`VERIFIED_FUNCTIONAL`**: Endpoint reachable and returns expected HTTP 200/201 response.
- **`VERIFIED_AUTH_REQUIRED`**: Endpoint reachable, returns HTTP 401/403 with valid documentation.
- **`VERIFIED_RATE_LIMITED`**: Endpoint reachable, returns HTTP 429 rate-limit headers.
- **`PARTIALLY_FUNCTIONAL`**: Documentation/spec verified, main endpoint partially working.
- **`SPEC_VERIFIED_ONLY`**: OpenAPI spec verified HTTP 200, backend endpoint unverified live.
- **`UNREACHABLE`**: Connection timeout or DNS failure (**REJECTED**).
- **`DEAD`**: Persistent HTTP 404 on base URL and docs (**REJECTED**).

---

## 23. Evidence Provenance Model

Every factual claim used in ranking MUST store evidence provenance to eliminate hallucination:

```json
"license_spdx": {
  "value": "MIT",
  "source_url": "https://github.com/searxng/searxng/blob/master/LICENSE",
  "source_type": "repository_license",
  "retrieved_at": "2026-08-17T05:00:00Z",
  "evidence_snippet": "Permission is hereby granted, free of charge...",
  "confidence": "HIGH"
}
```

---

## 24. Freshness Policy & Staleness Bands

Candidate APIs track 4 distinct timestamp checks:
- `repository_checked_at`
- `endpoint_checked_at`
- `documentation_checked_at`
- `release_checked_at`

### Freshness Bands
- **`FRESH`**: Checked < 7 days ago
- **`RECENT`**: Checked 7–30 days ago
- **`STALE`**: Checked 31–180 days ago (lowers maintenance score)
- **`VERY_STALE`**: Checked > 180 days ago (requires re-verification)

---

## 25. Search Query Expansion Strategy & Iterative Discovery

When initial search yield is low, generate expanded query families:

1. **Target Query**: `"target API"`
2. **Open Source Query**: `"target" open source API`, `"target" self hosted API`
3. **Protocol Query**: `"target" REST API`, `"target" GraphQL API`, `"target" gRPC API`
4. **Specification Query**: `"target" OpenAPI`, `"target" Swagger`, `"target" API schema`
5. **Repository Query**: `site:github.com target API`, `site:gitlab.com target API`
6. **Deployment Query**: `target Docker API`, `target self-hosted API`

---

## 26. Adaptive Candidate Discovery & Search Saturation

- **No Rigid Quotas**: Do not force a fixed candidate count (e.g. 500+). A niche target may have only 12 legitimate open-source APIs.
- **Search Saturation Rule**: Stop discovery when `new_valid_candidates / total_candidates < 10%` for 3 consecutive query iterations.
- **Never Fabricate**: Never create synthetic or fake candidates to fill numeric quotas.

---

## 27. 8-Point Capability Requirement Match Model

Evaluate target requirement match out of 25 points across 8 dimensions:
1. Target functionality match
2. Core endpoint capabilities
3. Input compatibility
4. Output compatibility
5. Search/query semantics
6. Authentication compatibility
7. Deployment compatibility
8. Intended use case

### Match Classification & Points
- **`EXACT_MATCH`** (25 pts): Direct official or complete open-source implementation of target.
- **`STRONG_MATCH`** (20 pts): Substantial component or major target API client.
- **`PARTIAL_MATCH`** (15 pts): Moderate capability coverage.
- **`ADJACENT`** (10 pts): Weak connection or indirect utility.
- **`IRRELEVANT`** (0 pts): Unrelated (**REJECTED**).

---

## 28. Endpoint Capability Extraction

Extract actual functional capabilities tags:
`capabilities: ["web_search", "image_search", "news_search", "autocomplete", "pagination", "filters", "language_support"]`

For every endpoint, document: `method`, `path`, `description`, `parameters`, `authentication`, `response_format`.

---

## 29. OpenAPI Semantic Validation Engine

Validate OpenAPI (2.0 / Swagger, 3.0, 3.1) specifications:
- Validate JSON/YAML syntax and schema structure
- Verify paths, HTTP methods, request bodies, and response schemas
- Detect empty paths, broken `$ref` references, and dead server URLs

---

## 30. GraphQL and gRPC Verification Logic

- **GraphQL**: Verify endpoint reachability, test introspection query (`{ __schema { queryType { name } } }`), validate schema, and execute test query.
- **gRPC**: Verify gRPC port reachability, test reflection service, discover `.proto` files, and extract service/method definitions.

---

## 31. Security Intelligence & Hard Vulnerability Rejection

- Check CVE databases, GitHub Security Advisories, TLS/SSL validity, and secret exposures in repository.
- **CRITICAL SECURITY REJECTION POLICY**: Candidates with unpatched critical CVEs or hardcoded credentials are **IMMEDIATELY REJECTED** (`rejection_code: SECURITY_RISK`).

---

## 32. License Compatibility Analysis

Classify license compatibility for project integration:
- **`PERMISSIVE`**: MIT, Apache-2.0, BSD-3-Clause (commercial & SaaS friendly)
- **`WEAK_COPYLEFT`**: LGPL, MPL-2.0
- **`STRONG_COPYLEFT`**: GPL-3.0, AGPL-3.0 (requires copyleft review)
- **`SOURCE_AVAILABLE_NON_OSI`**: Business Source License (BSL), Commons Clause
- **`UNKNOWN`**: Unspecified license

---

## 33. Usage Feasibility & Cost Normalization

Classify integration feasibility:
- **`FREE_UNLIMITED`**: Completely free public API
- **`FREE_LIMITED`**: Free tier with rate limits
- **`SELF_HOSTED_UNLIMITED`**: Open-source self-hostable instance
- **`PAID`**: Commercial subscription required
- **`MIXED`**: Freemium / hybrid model

---

## 34. Host Authority Classification

Distinguish official hosted infrastructure from third-party community mirrors:
- **`OFFICIAL_HOSTED`**: Endpoint hosted by official vendor organization
- **`OFFICIAL_DOCUMENTED`**: Official documentation with self-hosting instructions
- **`COMMUNITY_HOSTED`**: Third-party community deployment
- **`THIRD_PARTY_HOSTED`**: Unofficial mirror
- **`SELF_HOSTED_ONLY`**: Self-hosted codebase only

> Never treat a random third-party community instance as proof of official API availability.

---

## 35. Underlying Service Fingerprinting & Deduplication

Group duplicate candidate APIs by:
- Repository origin URL
- Package registry identity
- API server domain & schema hash
- Endpoint path & documentation similarity

### Fingerprint Classifications
`MIRROR` | `FORK` | `WRAPPER` | `HOSTED_INSTANCE` | `SDK_WRAPPER` | `ORIGINAL_PROJECT`

Retain only `ORIGINAL_PROJECT` or the highest-scoring implementation.

---

## 36. Transient Failure Handling & Retry Policy

Avoid false negatives caused by temporary network outages:
1. Immediate retry on connection error
2. Test alternate HTTP method if HEAD fails (try GET)
3. Retry after exponential backoff
4. Test alternate documented endpoint
5. Classify: `TRANSIENT_FAILURE` (retry later) | `PERSISTENT_FAILURE` | `DEAD`

---

## 37. Confidence Score Formula & Quality Score Separation

- **Quality Score (`overall_score`)** (0–100): *"How good is the API implementation and feature set?"*
- **Confidence Score (`confidence_score`)** (0–100 / `HIGH` | `MEDIUM` | `LOW`): *"How certain are we about our assessment?"*

$$	ext{Confidence Score} = 	ext{Evidence Completeness} + 	ext{Source Authority} + 	ext{Endpoint Verification} + 	ext{Spec Verification} + 	ext{Freshness} + 	ext{Cross-Source Agreement}$$

- `90-100` = `HIGH` confidence
- `70-89` = `MEDIUM` confidence
- `<70` = `LOW` confidence

---

## 38. Structured Failure Diagnostic Codes

Rejections MUST include a structured code in `rejection_codes`:
- `NO_SOURCE`: Source repository missing or deleted
- `INVALID_LICENSE`: Proprietary or non-compliant license
- `NO_IMPLEMENTATION`: Empty README without API codebase
- `DEAD_ENDPOINT`: Unreachable base URL and documentation
- `LOW_REQUIREMENT_MATCH`: Scored < 10/25 on requirement match
- `DUPLICATE`: Duplicate wrapper or fork of selected API
- `SECURITY_RISK`: Critical unpatched CVE or hardcoded secrets
- `STALE_PROJECT`: Abandoned codebase with broken infrastructure

---

## 39. Reproducibility & Audit Telemetry

Every search run records operational audit telemetry:
- `SEARCH_RUN_ID`
- `SEARCH_TIMESTAMP`
- `QUERY_SET`
- `SEARCH_SOURCES`
- `SKILL_VERSION` (`2.0.0`)
- `SCORER_VERSION` (`1.3.0`)

---

## 40. Deterministic Scoring Rule

$$	ext{Same Evidence} + 	ext{Same Scorer Version (1.3.0)} \implies 	ext{Identical Score}$$

Score calculations MUST be 100% deterministic across execution runs.

---

## 41. Source Authority Hierarchy & Conflict Resolution

When sources provide conflicting metadata:
- **For License**: Repository `LICENSE` file > Package Registry metadata > `README.md`
- **For API Status**: Live Endpoint HTTP Response > Official Developer Portal > `README.md`
- **For Version**: Official GitHub Release Tag > Package Registry > `README.md`
- **For Architecture**: Source Code Structure > Documentation > `README.md`

---

## 42. Top-10 Diversity Rule

The final Top 10 roster MUST preserve architectural and deployment diversity:
- Do not allow multiple forks or wrappers of the same underlying API to fill Top 10 slots.
- Ensure representation across REST, GraphQL, self-hostable Docker, and official SDKs.

---

## 43. Strict No-Synthetic-Data Rule

- ❌ NEVER invent base URLs, endpoints, OpenAPI specs, rate limits, or version numbers.
- ❌ Unknown values MUST be recorded as `null`, `UNKNOWN`, or `NOT_DOCUMENTED`.

---

## 44. Verified Code Samples Only

Code samples in Column 9 of Excel MUST be generated exclusively from verified endpoints, methods, and parameters documented in official specs. Never invent unverified parameters.

---

## 45. Result-Level Recommendation Badges

Top 10 selected APIs are assigned specific recommendation badges:
- `BEST_OVERALL`: Highest composite score and verified endpoints
- `BEST_FOR_SELF_HOSTING`: Full Docker Compose / K8s self-hosting support
- `BEST_NO_AUTH`: Public API with no authentication required
- `BEST_DOCUMENTED`: Valid OpenAPI 3.0 spec + Redoc / Swagger UI
- `BEST_DEVELOPER_ECOSYSTEM`: Multi-language official SDK support
- `BEST_LIGHTWEIGHT`: Minimal dependencies and fast response latency
- `BEST_ENTERPRISE`: High security score, OAuth2 auth, and compliance docs
- `BEST_OPEN_SOURCE_LICENSE`: OSI-approved permissive license (MIT / Apache-2.0)
