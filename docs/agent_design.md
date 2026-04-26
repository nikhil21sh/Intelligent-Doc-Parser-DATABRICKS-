# Agent Architecture Design

This document outlines the state graph for the IDP Orchestration Agent.

## State Object (TypedDict)
* `query`: string
* `retrieved_facilities`: list
* `reasoning`: dict
* `citations`: list
* `response`: string

## Node Flow
1. **Retrieve Node**: Calls `/search` (or `/facilities`) to fetch raw facility data.
2. **Reason Node**: Evaluates facilities against `query`, calls `/anomalies` and `/deserts`, and outputs structured JSON (gaps, flags, recommendations).
3. **Synthesize Node**: Transforms reasoning JSON into a human-readable narrative with inline citations.
4. **Respond Node**: Formats the final output for the UI.

**Execution Path:**
`[START] -> Retrieve -> Reason -> Synthesize -> Respond -> [END]`