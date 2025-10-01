# Placeholder selectors – update to match CDAsia's live DOM.
SEL = {
    # Login
    "login_user": "input[name='id']",
    "login_pass": "input[name='password']",
    "login_submit": "button[type='submit']",
    "post_login_marker": "nav .user-avatar",  # an element present only after login

    # Search form
    "search_division": "input[name='division']",
    "search_keywords": "input[name='q']",
    "search_year_from": "input[name='year_from']",
    "search_year_to": "input[name='year_to']",
    "search_submit": "button:has-text('Search')",

    # Results
    "results_container": "#results",
    "result_card": ".result-card",
    "card_title": ".result-title",
    "card_link": ".result-title a",
    "card_date": ".result-date",

    # Pagination
    "pagination_next": "button[aria-label='Next']",
    # Download link on detail page
    "download_link": "a:has-text('Download')"
}
