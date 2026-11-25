---
type: gotcha
title: A refused connection to a local port takes 2 s on Windows
description: Windows retries a refused loopback connect for about 2 s (4 s for localhost); probe with a short connect timeout.
tags: [windows, networking, verify, testing]
updated: 2026-11-25
---

# A refused connection to a local port takes 2 s on Windows

## Symptom
Checking whether a local server is up is slow on Windows only. A probe of a port nothing listens on returns after about 2 s, or 4 s for `localhost`, whatever the `timeout` passed to `urllib` or a socket. A polling loop meant to tick every 0.25 s ticks every 2 s. On Linux and macOS the same probe fails at once.

## Cause
Windows answers a connect to a closed loopback port by retrying it for about 2 s before reporting `WSAECONNREFUSED` (10061). `localhost` resolves to `::1` and then `127.0.0.1`, and each address pays it. `verify.py` hit this before each build start (the "something already answers" check) and on every poll while the build came up: about 10 s per verify run in `test_recorded_tests` (2026-11-25).

## Fix
For a URL on this machine, try the port with a short socket connect (0.5 s) first, and treat no accept as "not up". A listening local port accepts at once. Keep the normal request for other hosts. See `verify.nothing_listens_here`.
