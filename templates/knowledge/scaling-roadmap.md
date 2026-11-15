---
type: decision
title: Scaling roadmap
description: The steps this product's architecture takes as it grows, each with the trigger that justifies it.
tags: [architecture, scaling]
updated: [YYYY-MM-DD]
---

# Scaling roadmap

<!-- Written by sdlc setup with the approved stack's rows; the project's from now on. Add a row when a feature brings
     a piece with its own exit (an auth library, a database host), and update a row when a step is taken. -->

Take a step only when its trigger is met and the team decides; the steps are independent, so one change takes one
step. A change that takes a step is sized L.

| Step | Trigger | What changes | What stays |
|---|---|---|---|

<!-- Candidate rows. Setup copies into the table the rows whose "when" fits the approved stack, then deletes this
     comment; the deploy step adds the hosting rows once a target is chosen.

When one deployable (the API mounted in Nuxt or Next.js):
| Split the API into its own service | A second client appears (a mobile app, another web app, an outside caller); the API needs its own deploy or scaling cadence; background work slows the web app | Give the backend its own entry point and deploy it separately; serve the web app as static files; proxy `/api/*` to the new service to keep one origin | The backend code, the contract, the web app |

When the backend is node:
| Move hot paths to Go | Measurements show TypeScript is the bottleneck: CPU-heavy work, very high concurrency, or compute cost | Rewrite the heavy endpoints in Go against the same contract and route them by path at the proxy | The contract, the clients, the other endpoints |

When the backend is go:
| Extract a worker | Background work competes with request handling | A `cmd/worker` in the same module runs the same services from a queue or schedule, deployed as its own service or job | Services, store, contract |

When the backend is fastapi:
| Extract a worker | Background or CPU-bound work competes with request handling | A worker process runs the same services from a queue, deployed as its own service or job | Services, repositories, contract |

When there is a web or mobile app and an API:
| Add a BFF | One screen must combine data from several services; a third-party token must stay on the server; web and mobile need differently shaped data | A thin server between the clients and the services that holds the session, aggregates data and forwards requests, nothing else | The `/api/*` paths the clients call, the client-side queries |

When the PRD names one customer organization, or doesn't say:
| Turn on multi-tenancy | A second customer organization | Add organizations and memberships; resolve the tenant from the signed-in user's active organization; scope every table and query by it, with Row-Level Security where the database has it; prefix client cache keys with the tenant | Services, the contract, the clients |

When a deploy target is chosen (the deploy step):
| Change hosting | The host limits the runtime, cost or compliance, or infrastructure must sit with one provider | Swap the entry point and database client for the new host; move the database with dump and restore | Business code, schema, contract |

When the target is docker-compose and the database runs on that server:
| Move the database to a managed service | Customer data or an uptime commitment makes one server too risky, or nobody has time for restore drills | Dump and restore into a managed PostgreSQL, then change the connection string | Schema, queries, code |
-->
