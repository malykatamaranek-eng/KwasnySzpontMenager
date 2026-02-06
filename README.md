# KwasnySzpontMenager

Zaawansowana platforma marketplace oparta o architekturę mikroserwisową.
Projekt łączy globalną skalowalność z lokalnymi wymaganiami polskiego rynku
(Przelewy24, wielojęzyczność PL/EN, RODO/GDPR).

---

## Architektura ogólna

```
┌─────────────────────────────────────────────────────┐
│               Frontend (Next.js 14+)                │
├───────────────┬───────────────┬─────────────────────┤
│  Storefront   │  Vendor       │  Admin Dashboard    │
│  (kupujący)   │  Panel        │  + Analytics        │
└───────────────┴───────────────┴─────────────────────┘
                       │
               GraphQL Gateway
                       │
┌───────────────┬───────────────┬─────────────────────┐
│ Auth          │ Product       │ Order &              │
│ Service       │ Service       │ Payment Service      │
├───────────────┼───────────────┼─────────────────────┤
│ Search        │ Inventory     │ Notification         │
│ Service       │ Service       │ Service              │
└───────────────┴───────────────┴─────────────────────┘
```

## Struktura repozytorium

```
marketplace/
├── apps/
│   ├── storefront/            # Next.js 14 – interfejs kupującego
│   ├── vendor-panel/          # React + Vite – panel sprzedawcy
│   ├── admin-dashboard/       # Remix – panel administracyjny
│   └── mobile/                # React Native – aplikacja mobilna
├── packages/
│   ├── shared-types/          # Wspólne typy TypeScript
│   ├── design-system/         # Komponenty UI
│   └── utils/                 # Narzędzia pomocnicze
├── services/
│   ├── auth-service/          # NestJS – JWT, OAuth2, RBAC/ABAC
│   ├── product-service/       # Go – katalog, ceny, ElasticSearch
│   ├── order-service/         # Java Spring Boot – saga, outbox
│   ├── payment-service/       # Node.js – Stripe, Przelewy24
│   ├── search-service/        # Python + Elastic – NLP, rekomendacje
│   └── notification-service/  # Node.js – WebSocket, e-mail, SMS
└── infrastructure/
    ├── k8s/                   # Manifesty Kubernetes
    ├── terraform/             # Infrastruktura jako kod
    └── monitoring/            # Prometheus, Grafana
```

## Frontend – trzy aplikacje

| Aplikacja | Technologia | Cel |
|-----------|------------|-----|
| **Storefront** | Next.js 14, App Router, RSC, Tailwind + shadcn/ui, Framer Motion, Zustand, TanStack Query, NextAuth/Clerk, Stripe.js, Mapbox GL, i18next | Pełne doświadczenie kupującego |
| **Vendor Panel** | React 18 + Vite, MUI / Ant Design, React Admin, Recharts, React-DnD, React Hook Form + Yup | CRUD produktów, analityka sprzedawcy |
| **Admin Dashboard** | Remix / Next.js, Tremor / shadcn/ui, TanStack Table, Ag-Grid Enterprise, WebSocket | Zarządzanie platformą, monitoring |

## Backend – mikroserwisy

| Serwis | Język | Baza | Rola |
|--------|-------|------|------|
| **API Gateway** | Node.js + Fastify, GraphQL Mesh / Apollo Federation | — | Rate limiting, cache, load balancing |
| **Auth Service** | NestJS + TS | PostgreSQL | JWT, OAuth2, social login, RBAC + ABAC, Keycloak/Auth0 |
| **Product Service** | Go / Rust | PostgreSQL + TimescaleDB, Redis, ElasticSearch | Katalog, ceny, indeksowanie |
| **Order Service** | Java Spring Boot / .NET | PostgreSQL + Redis | Saga pattern, outbox, event sourcing |
| **Payment Service** | Node.js + TS | PostgreSQL | Stripe / Przelewy24, webhook, idempotency |
| **Search Service** | Python + ElasticSearch | ElasticSearch, Typesense / Algolia | Pełnotekstowe, NLP, vector search |
| **Notification Service** | Node.js + WS | Redis, Kafka | Socket.io, Firebase, Resend, Twilio |

## Bazy danych i cache

| Technologia | Zastosowanie |
|-------------|-------------|
| **PostgreSQL 16** + PostGIS + TimescaleDB + Citus | Dane główne, geolokalizacja, serie czasowe, sharding, Row Level Security |
| **MongoDB 7** | Recenzje, czat, logi aktywności |
| **Redis Stack** | Cache, sesje, Pub/Sub, rate limiting, JSON + Search |
| **ElasticSearch 8** | Full-text + faceted search, autocomplete, rekomendacje, logi |

## Moduły funkcjonalne marketplace

1. **Katalog produktów** – wariacje (S/M/L), dynamiczne ceny, filtry, porównywarka
2. **System zamówień** – multi-vendor cart, split payments, tracking, zwroty
3. **Płatności** – wiele metod, escrow, payouts, subskrypcje, wielowalutowość
4. **Oceny i recenzje** – gwiazdki, zdjęcia/video, moderacja, analityka
5. **Komunikacja** – in-app messaging, live chat, centrum powiadomień, e-mail/SMS
6. **Analizy** – dashboard sprzedawcy, śledzenie zachowań, prognozowanie, A/B testing

## AI / ML (mikroserwisy Python)

- **Recommendation Engine** – collaborative filtering, content-based, real-time
- **Fraud Detection** – wykrywanie anomalii, modele ML, scoring ryzyka
- **Search Relevance** – NLP, semantic search, auto-tagging

## Real-time

- Socket.io / WebSocket, Server-Sent Events
- WebRTC (video chat), Redis Pub/Sub, Kafka Streams

## Bezpieczeństwo i compliance

- OWASP Top 10, CSP, CORS, CSRF
- Rate limiting (Redis), DDoS protection (Cloudflare)
- GDPR / RODO, PCI DSS (płatności)
- Audit logging, szyfrowanie danych at rest

## Observability

- OpenTelemetry → Jaeger / Tempo (tracing)
- Prometheus (metryki) → Grafana (dashboardy)
- Loki (logi), Sentry (błędy), Datadog / New Relic (APM)

## CI/CD

- GitHub Actions – testy jednostkowe, integracyjne, E2E (Playwright)
- Security scanning (Snyk, Trivy)
- Docker build → push → Kubernetes deployment
- Canary releases, ArgoCD (GitOps)

## Fazy rozwoju

### Faza 1 – MVP
Next.js (monolith frontend) · NestJS (monolith backend) · PostgreSQL + Prisma · Redis · Stripe · Vercel + Railway

### Faza 2 – Skalowanie
Mikroserwisy · GraphQL Federation · Kafka · ElasticSearch · Kubernetes · Service mesh (Istio / Linkerd)

## Data pipeline / BI

Apache Kafka → Apache Flink / Spark → BigQuery / Snowflake → Metabase / Looker Studio · dbt

---

> Projekt zakłada zespół 10+ osób, pełny custom development od zera
> z myślą o globalnej skali, odporności na duże obciążenia
> oraz integracji z polskim ekosystemem płatności.