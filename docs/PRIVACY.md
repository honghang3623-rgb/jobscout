# Privacy and publication boundaries

The public repository was built from an explicit source-file allowlist in a new directory and new Git history. It is not a copy of the personal runtime directory or its history.

Excluded from publication:

- Actual candidate profiles, résumé files, school and employer history, contact information, personal availability and authorization plans.
- SQLite files, application stages and notes, collected job descriptions, browser snapshots, logs, preferences, backups and exports.
- API credentials, authentication cookies, session tokens, local launcher bundles, absolute home-directory paths and screenshots of personal runtime data.
- Vendored third-party libraries; optional dependencies are declared through `requirements.txt`.

The committed profiles, 2030 graduation setting and sample jobs are fictional. Regression-test dates are test fixtures. The real employer registry contains public career-site configuration, not the author's application history.

At runtime, local profiles and `data/` are ignored by Git. The privacy checker inspects tracked or candidate source files for forbidden artifacts and common credential/contact patterns. This is a release guard, not a guarantee that arbitrary future edits contain no sensitive data; review the staged diff before every publication.

The local API binds to loopback. This repository does not configure a public internet server, reverse proxy or cloud deployment. Adding network exposure would require a separate authentication and security design.

Optional AI analysis transmits the selected profile and JD to the configured provider only when invoked. Live collection contacts employer/ATS sites. The application neither logs into personal recruiting accounts nor submits applications automatically.

Publishing under a GitHub account makes that account and repository ownership visible. The project package itself does not include private identity or contact fields.
