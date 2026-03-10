import os
import subprocess

def get_one_liner(file_path):
    # Uses the Gemini CLI to summarize the file
    # We use a timeout to prevent the script from hanging on large files
    # Prefer calling the `gemini` CLI directly; if it isn't available
    # or returns no output, fall back to a simple local summary
    prompt = f"Summarize the core concept of this file in exactly one sentence for a directory index: @{file_path}"
    try:
        result = subprocess.run(["gemini", "-p", prompt], capture_output=True, text=True, timeout=15)
        out = (result.stdout or "").strip()
        if out:
            return out
    except FileNotFoundError:
        # `gemini` not installed
        pass
    except Exception:
        # Any other runtime issue (timeout, non-zero exit, etc.) -> fall back
        pass

    # Fallback: return the first non-empty line or first sentence from the file
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as rf:
            for line in rf:
                line = line.strip()
                if line:
                    import re
                    parts = re.split(r'(?<=[.!?])\s+', line)
                    return parts[0] if parts else line
    except Exception:
        pass

    return "Summary unavailable."

def get_crm_data_path():
    # Attempt to load the path from .env in the logic root
    logic_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(logic_root, ".env")
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('CRM_DATA_PATH='):
                    path = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if not os.path.isabs(path):
                        path = os.path.abspath(os.path.join(logic_root, path))
                    return path
    return os.getenv("CRM_DATA_PATH", os.getcwd())

def generate_index(directory=None):
    if directory is None:
        directory = get_crm_data_path()
    
    index_file = "GEMINI_INDEX.md"
    index_path = os.path.join(directory, index_file)

    # Open the index file in the target directory so running the script
    # from another cwd still updates the project's index
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# Project Semantic Map\n\n")
        f.write("> This file provides a one-sentence overview of every relevant file in the project root.\n\n")
        
        for root, dirs, files in os.walk(directory):
            # 1. Skip hidden directories like .git or .obsidian
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                # 2. Only index text-based files and skip the index itself/this script
                if file.endswith((".md", ".txt", ".py", ".js")) and file != index_file and file != os.path.basename(__file__):
                    path = os.path.join(root, file)
                    # Use a relative path for the index display
                    rel_path = os.path.relpath(path, directory)
                    
                    print(f"Indexing: {rel_path}...") # Visual feedback in terminal
                    summary = get_one_liner(path)
                    f.write(f"- **{rel_path}**: {summary}\n")

if __name__ == "__main__":
    generate_index()