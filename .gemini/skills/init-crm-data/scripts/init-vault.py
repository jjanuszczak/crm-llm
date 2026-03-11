import os
import sys
import subprocess

def init_vault(name):
    logic_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
    vault_path = os.path.join(logic_root, name)
    
    if os.path.exists(vault_path):
        print(f"Error: Directory '{name}' already exists.")
        return False

    print(f"Initializing new CRM Data Vault at: {vault_path}...")
    
    # 1. Create Folders
    folders = [
        "Accounts", "Contacts", "Opportunities", "Deals", 
        "Activities", "Tasks", "Reports", ".obsidian"
    ]
    for folder in folders:
        os.makedirs(os.path.join(vault_path, folder), exist_ok=True)
    
    # 2. Git Init in Vault
    subprocess.run(["git", "init"], cwd=vault_path)
    
    # 3. Local Gitignore
    with open(os.path.join(vault_path, ".gitignore"), 'w') as f:
        f.write(".DS_Store\n.obsidian/workspace.json\n")
    
    # 4. Initial Files
    with open(os.path.join(vault_path, "DASHBOARD.md"), 'w') as f:
        f.write("# CRM Dashboard\n\n**Last Updated:** Never\n\n## Engaged Opportunities\n\n## Active Pipeline\n\n## Upcoming Tasks\n")
    
    with open(os.path.join(vault_path, "GEMINI_INDEX.md"), 'w') as f:
        f.write("# Gemini Index\n\nInitial index for this CRM vault.")

    # 5. Main Repo Gitignore Protection
    main_gitignore = os.path.join(logic_root, ".gitignore")
    if os.path.exists(main_gitignore):
        with open(main_gitignore, 'r') as f:
            lines = f.readlines()
        
        entry = f"{name}/\n"
        if entry not in lines:
            print(f"Adding '{name}/' to main .gitignore...")
            with open(main_gitignore, 'a') as f:
                f.write(f"\n# Nested Data Vault\n{entry}")

    print(f"\nSuccess! Vault '{name}' initialized.")
    print(f"To use this vault, update your .env file: CRM_DATA_PATH=./{name}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 init-vault.py <directory-name>")
    else:
        init_vault(sys.argv[1])
