# Skill: Create Contact

## Description
Creates a new contact file in the `CRM_DATA_PATH/Contacts/` directory for a specified individual. This skill automates file creation, populates the v4 Contact frontmatter, and performs web research to generate a professional profile with useful engagement context.

## Usage
`create-contact "Full Name" --company "Company Name" --linkedin "LinkedIn URL" --email "email@address.com"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **File Naming:**
    *   Convert the `name` to `Firstname-Lastname.md` format (e.g., `John-Garfin.md`).
    *   Check if `CRM_DATA_PATH/Contacts/[Firstname-Lastname].md` already exists. If it does, stop and notify the user.

3.  **Web Research (If `linkedin` is provided or `company` is known):**
    *   **Search 1:** Google search for `"[Name]" "[Company]" LinkedIn` to find the profile if not provided.
    *   **Search 2:** Google search for `"[Name]" "[Company]" awards recognition "little known" facts` to find unique engagement angles.
    *   **Search 3:** Google search for `"[Name]" site:twitter.com OR site:instagram.com` (optional) to find personal interests.

4.  **Content Generation (Using `templates/contact-template.md`):**
    *   **Frontmatter:**
        *   `id`: Stable machine-friendly contact ID.
        *   `full-name`: The contact's full name.
        *   `nickname`: The contact's first name or preferred nickname.
        *   `owner`: Default to the primary operator.
        *   `account`: `[[Company Name]]` (if provided).
        *   `linkedin`: The provided LinkedIn URL.
        *   `email`: The provided email address.
        *   `mobile`: The provided mobile number.
        *   `source`: Default to `manual` or another explicit origin such as `lead-conversion`.
        *   `source-ref`: Optional provenance link, especially when the Contact is created from a Lead.
        *   `relationship-status`: Default to `active`.
        *   `priority`: Default to `medium` unless a stronger signal is known.
        *   `date-created`: Current date (YYYY-MM-DD).
        *   `date-modified`: Current date (YYYY-MM-DD).
    *   **Body Sections:**
        *   **Header:** `# **Profile: [Name]**`
        *   **Section 1: Professional Overview**
            *   Extract current role and key responsibilities from search results.
            *   Highlight core expertise and professional focus.
        *   **Section 2: Strategic Insights & "Little Known" Facts**
            *   Synthesize unique findings (awards, publications, interesting career pivots, hobbies).
        *   **Section 3: Engagement Hooks for Forging Connection**
            *   Draft 3 distinct conversation starters based on the research.
        *   **Section 4: Actions**
            *   Create a "Search Email" link: `[Search Email](https://mail.google.com/mail/u/0/#search/[email_address])`.

5.  **File Creation:**
    *   Write the generated content to `CRM_DATA_PATH/Contacts/[Firstname-Lastname].md`.

6.  **Compatibility Note:**
    *   `full-name` is the canonical name field.
    *   Legacy `full--name` may still exist in older vault files, but new records must not use it.

7.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add Contacts/[Firstname-Lastname].md && git commit -m "agent: created contact [Firstname-Lastname]"
        ```
    *   Run `update-dashboard` to reflect the new contact.

8.  **Output:**
    *   Confirm the file creation to the user and display the path.
