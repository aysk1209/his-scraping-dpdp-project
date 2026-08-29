"""Scraping / extraction layer.

Build step 4. Tier 2 methodology: credentialed headless-browser automation.
Built adapter-style — downstream code depends only on the `HISDataSource`
interface in `base`, never on a concrete adapter, so `adapters.mock_his` and
`adapters.live_his` are interchangeable via configuration.
"""
