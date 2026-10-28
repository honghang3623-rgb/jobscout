# Design decisions

## Separate markets, shared storage

U.S. authorization evidence and employer filing history belong to the U.S. workflow. China recruitment cohorts, internship attendance and domestic city filters belong to a separate board. Both share persistence and review components without treating market-specific constraints as interchangeable.

## Unknown is a distinct state

A missing sponsorship statement is not approval. An unknown deadline is not rolling recruitment. A skill keyword is not demonstrated experience. Screening keeps the requirement, its evidence and its uncertainty visible.

## Partial feeds must not erase jobs

Collectors report whether pagination was complete. A repeated page or failed response is an error rather than an empty successful feed. Only complete results may mark missing source jobs closed. Browser snapshots are explicitly partial and preserve the original timestamp.

## Local-first operation

The core workflow uses standard-library Python and SQLite. Optional AI and XLSX capabilities are separate. The public edition starts with fictional data and scanning disabled, so a reviewer can inspect the interface without credentials or network collection.

## AI-assisted development

AI coding assistants supported implementation and iterative debugging. The work is presented as a personal product and engineering project, with human-defined requirements and human decisions before applications. The repository does not claim production deployment, job offers, interview outcomes or measured matching accuracy.
