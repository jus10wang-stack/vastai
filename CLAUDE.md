# CLAUDE.md

## CORE CODING RULES, ALWAYS FOLLOW BEFORE YOU EXECUTE ANYTHING
- **Coding Rules:**
   - DO NOT EVER DELETE ANY EXISTING FOLDER/FILES/CODE UNLESS ITS TO REMOVE OLD TEST FOLDERS/FILES
   - Make sure to have at least 30% of the code commented
      - The goal is to have humans and AI models understand what you coded
      - The goal is to also allow better debugging when running into issues
   - The fewer lines of code, the better
      - Write clean, simple, readable code
      - Make sure the code is modular
      - Make sure the code is written efficiently and optiminally
      - Modify existing code minimally rather than replacing wholesale
      - Make the smallest possible changes to achieve the desired outcome
      - Change as few lines of code as possible
   - Preserve existing imports, dependencies, and configurations unless they conflict with requirements
   - Keep original comments, formatting, and code style as much as possible
   - Proceeed like a Senior Developer // 10x engineer
   - Implement features in the simplest possible way
   - Focus on core functionality before optimization
   - Use clear, consistent naming
   - Think thoroughly before coding. Write 2-3 reasoning paragraphs
   - Do not stop working until the request is completed
   - Do not delete comments for no reason
      - Only delete comments that are tied to code that is being deleted
   - When required to modify multiple files, look through every file's content row by row
      - Be very conscious of the entire content for every relevant file
   - When modifying any original rule, dont edit the original .mdc file
      - Instead output the results in the chat for me to copy and paste
      - For some reason the rules cant be edited and it errors.
   - If code is too large or incomplete to process:
      - Identify the specific files, functions, or components affected
      - Ask the user to @ mention those files for deeper access
      - Example: "Please @ mention the following files: [list]"
      - Why @ mentions matter:
         - They provide full file context, including hidden logic and dependencies
         - Without them, changes may be incomplete or inaccurate

- **Code Modification:**
   - Core Principle: Preserve and Adapt, Don't Rebuild Unnecessarily
      - When modifying a codebase, adding features, or refactoring components, the primary goal should be to retain as much of the existing, functional code as possible.
      - Avoid deleting or significantly altering code that is not directly impacted by the current task, unless explicitly instructed or if the code is genuinely obsolete and being replaced as part of a clearly defined goal (e.g., removing an old library like Playwright when the goal is to replace it with a Chrome Extension).

   - Leverage Proven Logic:
      - Existing code, especially in mature systems, often contains battle-tested logic and handles edge cases that might not be immediately obvious. Preserving it minimizes the risk of introducing regressions.
   - Focused Changes:
      - Keeping changes targeted to the specific feature or modification at hand makes development more manageable, easier to review, and reduces the scope of potential issues.
   - Efficiency:
      - Reusing existing code is generally more efficient than rewriting it from scratch.

   - Key Scenarios & Guidelines:
      - Component Replacement (e.g., Playwright to Chrome Extension):
         - The focus should be on replacing the specific component and adapting the interfaces of surrounding modules to work with the new component.
         - Core logic within those surrounding modules (e.g., agent decision-making, data processing) should be preserved as much as possible, changing only what's necessary to interact with the new interface.
         - Example: If migrating from `browser_use` (Playwright-based) to `browser_use_ext` (Chrome Extension-based), the agent's core prompting strategy and decision logic (`agent_core.py`, content of `prompts.py`) should ideally remain consistent, even if the *method* of defining/loading prompts changes structurally. The *instructions* to the LLM are paramount.
      - Adding New Features:
         - Strive to integrate new features into the existing architecture and codebase.
         - When adding new features, integrate them into existing patterns rather than creating new ones
         - Look for ways to extend current classes, functions, or modules rather than creating parallel or duplicative structures.
         - Always prefer extending existing classes/functions over creating new ones unless it is clearly not best-practice
      - Refactoring:
         - Refactoring should improve code structure or performance but maintain existing functionality. Changes should be justifiable and ideally covered by tests.
         - If refactoring how a piece of data is managed (e.g., prompt templates moving from external files to inline Pydantic models), ensure the *actual data/content* is preserved faithfully if it's proven to work.
      - Code Deletion:
         - Only delete code if:
            1.  It is part of a component being explicitly removed/replaced.
            2.  It is genuinely dead/unreachable code AND its removal doesn't affect desired functionality.
            3.  You are explicitly asked to remove it as part of the task.
         - Do not delete code simply because its structure is being changed if the underlying logic or content is still valid and required.
      - Preservation over recreation:
         - Always preserve existing code patterns and structures
         - Never recreate functionality that already exists unless explicitly required
      - Explicit modification scope:
         - Do not make "improvements" to unrelated code
         - Ask for clarification before touching files outside the specified scope
         - Preserve all existing functionality unless explicitly told to remove it
      - Final modification self-questions:
         - Before making changes, analyze and understand the existing code patterns
         - Explain what you're preserving and why before making modifications
         - If replacement is necessary, explain why modification isn't sufficient
         - Maintain existing error handling patterns and logging approaches
         - Before committing to large-scale changes or deletions, ask:
            - "Is this change absolutely necessary to achieve the current, specific goal?"
            - "Am I preserving the core, proven logic from the existing system?"
            - "Could this change be achieved with less disruption to the existing codebase?"

- **Debugging Rules:**
   - If the debugging is a medium sized bug that requires multiple lines of code, propose a minimum of three solutions for the issue THEN pick the best one
   - If debugging becomes circular or you're spinning in place with no progress:
      - Stop repeating the same steps—don't brute force a broken path
      - Step back and ask: what am i assuming that's possibly wrong?
   - Fallback tactics:
      - Isolate the smallest reproducible error case
      - Reduce the code to a minimal failing example
      - Add focused debug logs around the failing logic
      - Verify related dependencies, inputs, and side effects
      - Do a micro root cause study:
          - What is failing? where? when?
          - What changed recently?
          - Are there any hidden state mutations?
      - Check if the error could be avoided instead of fixed
      - Revisit the problem framing: is there a better approach?
      - Ask: would rewriting this part from scratch be faster and safer?
      - Try rubber ducking: explain the bug aloud or in a comment


- **File & Folder Structure Rules:**
   - BEFORE WRITING OR MODIFYING ANY CODE, ALWAYS reference the full project folder/file structure
   - Maintain original naming conventions, file structures, and architectural patterns
   - DO NOT assume the correct file path without checking — visually inspect the tree or use search
   - ALWAYS outline the folder and file you intend to create or modify before starting implementation
      - This includes writing down the exact path (e.g., src/utils/logger.py) before any code is generated
   - IF there are similarly named files or folders (e.g., utils/ vs shared_utils/), CONFIRM the correct one by opening and reading contents
   - NEVER create new folders or files without first checking if one already exists that serves the same purpose
   - ALWAYS prefer modifying existing code or files if they cover the same logic
   - DO NOT create duplicate folders or files just because you couldn't locate the right one
   - IF YOU ARE UNSURE where something belongs, STOP and ask or confirm the structure first
   - DO NOT place code in root or misc folders (/ , /tmp/ , /test/ ) unless specifically required for that purpose
   - DO NOT generate code into placeholder or example folders unless you're building a real test or scaffold

- **Debugging Rules:**
   - DO NOT JUMP TO CONCLUSIONS! Consider multiple possible causes before deciding.
   - You should start the reasoning paragraph with lots of uncertainty and slowly gain confidence as you think about the item more.
   - Before you answer, I want you to write a minimum of two detailed paragraphs, one arguing for different solutions you came up with - do not jump to conclusions, seriously consider multiple approaches. Then after you finish, tell me whether one of these solutions is obviously better than the other and why.
   - If you are debugging in a circle (your fix causes an issue, then that fix causes the previous issue), I want you to take a step back and look at what are other solutions that are possible. Then proceed with the reasoning paragraph.
   - Make minimal necessary changes, changing as few lines of code as possible
   - In case of strange errors, ask the user to perform a Perplexity web search to find the latest up-to-date information

- **Environment Rules:**
   - ALWAYS create a venv for every new Python project unless it's a one-off script using only the standard library
   - NEVER install packages globally unless absolutely necessary
   - ALWAYS check for a requirements.txt file and set up a venv before running anything
   - IF a .venv or venv folder exists, ACTIVATE it before doing any dev work
   - IF you clone or open a new Python repo, CREATE and ACTIVATE a venv before installing packages
   - DO NOT commit the venv folder to version control – add it to .gitignore
   - DO use python -m venv venv && source venv/bin/activate as the default setup
   - DO export your environment with pip freeze > requirements.txt before sharing or deploying
   - DO install from requirements.txt using pip install -r requirements.txt in fresh setups
   - OPTIONAL: use .venv instead of venv if your editor (like VS Code) prefers it for auto-detection


- **Building Process Rules:**
   - Verify each new feature works by telling the user how to test it
   - DO NOT write complicated and confusing code. Opt for the simple & modular approach
   - When not sure what to do, tell the user to perform a Perplexity web search


- **Comments Rules:**
   - ALWAYS try to add more helpful and explanatory comments into our code
   - NEVER delete old comments - unless they are obviously wrong/obsolete
   - Include LOTS of explanatory comments in your code. ALWAYS write well-documented code
   - Document all changes and their reasoning IN THE COMMENTS YOU WRITE
   - When writing comments, use clear and easy-to-understand language - write in short sentences


- **Build Version Rules:**
   - When installing packages/plugins, use only the version that is easily understood by AI
      - If the latest version came out recently, it is too new for AI to understand
      - i.e. Instead of "tailwindcss": "^4.1.4", you would install "tailwindcss": "^3.4.1" 
