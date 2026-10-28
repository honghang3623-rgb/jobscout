# JobScout interactive demo

Buildless, fictional-data demonstration of the JobScout workbench. `dist/` is the complete static site. No accounts, server API, credentials, private profiles or application database are included. Status and note changes exist only in browser memory until reload.

Run `node test-demo.cjs`, then serve `dist/` with a static web server. Rules and eligibility results were generated from the fictional fixtures by the public Python project at https://github.com/honghang3623-rgb/jobscout.

The online demo supports market switching, filters, precomputed matching evidence, a sample JD selector, notes/status changes, safe CSV exports and resetting. Live collection, AI calls, personal-file uploads and application submission are unavailable.
