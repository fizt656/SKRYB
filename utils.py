import re

def sanitize_filename(name):
    """Removes or replaces characters invalid for filenames/directory names."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'[\s.,;!]+', '_', name)
    return name[:100]

def get_user_input(prompt_message, multi_line=False):
    """Gets input from the user, optionally allowing multi-line."""
    print(prompt_message)
    if not multi_line:
        while True:
            user_input = input("> ").strip()
            if user_input:
                return user_input
            else:
                print("Input cannot be empty. Please try again.")
    else:
        lines = []
        print("(Enter 'EOF' on a new line when finished)")
        while True:
            try:
                line = input()
                if line.strip().upper() == 'EOF':
                    if lines:
                        return "\n".join(lines)
                    else:
                        print("Input cannot be empty. Please try again.")
                else:
                    lines.append(line)
            except EOFError: # Handle Ctrl+D
                if lines:
                    return "\n".join(lines)
                else:
                    print("Input cannot be empty. Please try again.")
