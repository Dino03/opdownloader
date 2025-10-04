# Selector map aligned with the Material-UI based CDAsia portal.
SEL = {
    # Login
    "login_user": "input[name='id']",
    "login_pass": "input[name='password']",
    "login_submit": "button[type='submit']",
    "post_login_marker": "nav .user-avatar",  # an element present only after login

    # Search form controls
    "search_library_button": "#library-menu-button",
    "search_library_menu": "#library-menu-listbox, [role='listbox'][aria-labelledby='library-menu-button'], [role='listbox'][id*='menu']",
    "search_library_option": "[role='option'][data-value='{library}'], li.MuiMenuItem-root[data-value='{library}'], [role='option']:has-text('{library}')",
    "search_backdrop": "div.MuiBackdrop-root",
    "search_section_chip": "button.MuiButtonBase-root:has-text('{section}')",
    "search_division_chip": "button.MuiButtonBase-root:has-text('{division}')",
    "search_title_input": "#input-Title",
    "search_number_input": "#input-Number",
    "search_ponente_input": "#input-Ponente",
    "search_citation_input": "#input-Citation",
    "search_court_input": "#courts",
    "search_submit": "#submit_btn",

    # Results table
    "results_container": "table.MuiTable-root tbody",
    "result_row": "table.MuiTable-root tbody tr",
    "result_ref": "td:nth-of-type(1)",
    "result_title": "td:nth-of-type(2)",
    "result_date": "td:nth-of-type(3)",

    # Pagination
    "pagination_next": "button[aria-label='Go to next page']",

    # Download link on detail page (toolbar icon button)
    "download_link": "button[aria-label='Download']"
}
