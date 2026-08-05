---
name: Recent News
description: Recent developments, campaigns, and announcements from the advertiser
queries:
  - '"{brand}" news announcements latest'
  - '"{brand}" campaign launch partnership'
  - '"{brand}" advertising sponsorship {year}'
topic_queries:
  - '"{brand}" {topic} news {year}'
  - '"{brand}" {topic} campaign launch'
max_results_per_query: 3
timelimit: "y"
---

Summarise the following search results about {brand} into a detailed digest of recent activity:

- New campaigns or marketing initiatives (include campaign names and themes)
- Product launches or updates
- Partnerships, sponsorships, or collaborations
- Changes in leadership, strategy, or brand direction
- Any other developments relevant to an advertising partner

Focus on developments from the last 6 months. Deprioritise or exclude anything older unless it is exceptionally significant. Include dates where available. Cite your sources as inline markdown links, e.g. [Source Title](url). If results are thin or outdated, note that.

Search results:
{search_results}
