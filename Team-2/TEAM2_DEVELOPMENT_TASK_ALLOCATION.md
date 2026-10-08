# MarketLens Team 2 --- Development Task Allocation

## Current State

Team 2 has completed the core MVP flow:

    Team 1 Asset API
            |
            v
    MarketLens Analysis Engine
            |
            v
    Finding Generation
            |
            v
    Explanation Context
            |
            v
    Gemini Explain Finding

The next development phase starts from this stable Explain Finding
implementation.

The development is divided into two tracks:

                     Team 2 Current System
                             |
              +--------------+--------------+
              |                             |
              v                             v

          Explore API                 Comparison Feature
           (2 people)                    (1 person)

              |                             |
              +--------------+--------------+
                             |
                             v

              Final Market Intelligence Integration

------------------------------------------------------------------------

# Track 1 --- Explore API Development (2 People)

## Goal

Improve Market Intelligence by adding more context and evidence through
additional APIs.

This track enriches the existing flow:

    API Data
       |
       v
    Finding
       |
       v
    Explanation

------------------------------------------------------------------------

## Developer 1 --- API Research & Provider Layer

Responsibilities:

-   Research additional API sources
-   Select useful market/company data
-   Build API connectors
-   Normalize external responses

Possible additional data:

-   Company profile
-   Sector/subsector information
-   Financial ratios
-   Historical metrics
-   Corporate actions
-   Market indicators
-   News/event context (if available)

Suggested structure:

    marketlens/

        providers/
            company.py
            financial.py
            market.py

Flow:

    External API
          |
          v
    Provider Layer
          |
          v
    Structured Data

------------------------------------------------------------------------

## Developer 2 --- Grounding & Intelligence Integration

Responsibilities:

-   Integrate additional API data into MarketLens flow
-   Extend explanation context
-   Ensure Gemini receives richer evidence
-   Maintain existing Explain Finding behavior

Current:

    Team 1 API
        |
        v
    Finding
        |
        v
    Gemini Explanation

Future:

    Team 1 API
        |
    Additional APIs
        |
        v
    Grounding Context
        |
        v
    Finding
        |
        v
    Gemini Explanation

Main files:

    marketlens/grounding.py
    marketlens/engine.py
    marketlens/llm.py

------------------------------------------------------------------------

# Track 2 --- Comparison Feature (1 Person)

## Goal

Create a separate comparison capability using existing MarketLens
findings.

The comparison feature extends MarketLens from single-asset analysis
into multi-asset analysis.

------------------------------------------------------------------------

## Responsibilities

-   Design comparison schema
-   Build comparison logic
-   Compare existing findings
-   Handle missing evidence
-   Add comparison endpoint

------------------------------------------------------------------------

## Comparison Scope

Comparison can analyze:

-   Fundamental evidence
-   Market activity
-   Investor flow
-   Research relevance alignment
-   Limitations

The feature should remain evidence-based.

It should not:

-   Provide buy/sell recommendations
-   Predict future returns
-   Create unsupported conclusions

------------------------------------------------------------------------

## Suggested Structure

    marketlens/

        comparison.py
        schemas.py

Example endpoint:

    POST /api/profiles/{profile_id}/comparison

Request:

``` json
{
  "symbols": [
    "BBCA",
    "BBRI"
  ]
}
```

------------------------------------------------------------------------

# Final Integration

After both tracks are complete:

                     External APIs
                          |
                          v
                  Grounding Context
                          |
                          v
                 MarketLens Engine
                          |
                  +-------+-------+
                  |               |
                  v               v

          Explain Finding     Comparison Feature

                  |
                  v

           Market Intelligence Dashboard

------------------------------------------------------------------------

# Development Priority

Recommended order:

1.  Keep Explain Finding stable
2.  Develop Explore API improvements
3.  Improve finding context quality
4.  Develop Comparison Feature
5.  Integrate final dashboard experience

------------------------------------------------------------------------

# Final Goal

The final MarketLens system should provide:

-   Richer market context
-   Better evidence-based explanations
-   Multi-asset comparison capability
-   Stronger Market Intelligence experience

Explore API and Comparison are separate development tracks that will
eventually be integrated into one MarketLens intelligence platform.
