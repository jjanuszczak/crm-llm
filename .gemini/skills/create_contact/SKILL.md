# Skill: Create Contact

## Description
Creates a new contact file in the `CRM_DATA_PATH/Contacts/` directory for a specified individual. This skill automates the file creation, populates the YAML frontmatter with provided details, and performs web research to generate a comprehensive professional profile, including "little known" facts and engagement hooks, using the `Templates/contact-template.md` structure.

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

4.  **Content Generation (Using `Templates/contact-template.md`):**
    *   **Frontmatter:**
        *   `full--name`: The contact's full name.
        *   `nickname`: The contact's first name or preferred nickname.
        *   `account`: `[[Company Name]]` (if provided).
        *   `linkedin`: The provided LinkedIn URL.
        *   `email`: The provided email address.
        *   `mobile`: The provided mobile number.
        *   `source`: Default to `network`.
        *   `status`: Default to `qualified`.
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

6.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add Contacts/[Firstname-Lastname].md && git commit -m "agent: created contact [Firstname-Lastname]"
        ```
    *   Run `update-dashboard` to reflect the new contact.

7.  **Output:**
    *   Confirm the file creation to the user and display the path.
