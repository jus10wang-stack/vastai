  # GitHub User Configuration Implementation Guide

  ## Overview

  This implementation adds support for configurable GitHub usernames in workflow configurations, allowing different
  users/forks to use their own GitHub repositories for provisioning scripts without hardcoding URLs.

  ## Problem Statement

  Previously, the provisioning script URL was hardcoded in `create_instance.py`:

  ```python
  "PROVISIONING_SCRIPT":
  f"https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/{provisioning_script}"

  This caused issues when:
  - Users forked the repo to their own GitHub accounts (e.g., jus10wang-stack/vastai)
  - The provisioning script downloaded from the wrong repo
  - Workflows failed to load because the script URL was incorrect

  Solution Architecture

  Three-Level Priority System

  1. Full URL (Highest Priority)
    - If provisioning_script is already a full URL, use it as-is
    - Example: "https://raw.githubusercontent.com/alice/vastai/.../script.sh"
  2. Config-Specified GitHub User
    - If config contains github_user, construct URL from it
    - Example: "github_user": "jus10wang-stack" → Uses jus10wang-stack repo
  3. Environment Variable
    - If no config value, check VASTAI_GITHUB_USER env var
    - Example: export VASTAI_GITHUB_USER="alice"
  4. Default Fallback (Lowest Priority)
    - If nothing else specified, default to "jiso007"
    - Ensures backwards compatibility

  Auto-Detection in Workflow Analyzer

  The workflow analyzer (vai workflow analyze) automatically detects the GitHub username from the current Git repository and
  populates the config file.

  Implementation Steps

  Step 1: Update create_instance.py

  Location: SCRIPTS/python_scripts/components/create_instance.py

  1.1: Add Helper Function

  Insert this function before create_instance() (around line 13):

  def get_provisioning_script_url(provisioning_script, github_user=None, github_branch="main"):
      """
      Get provisioning script URL with flexible configuration options.
      
      Supports three modes:
      1. Full URL: Use the provided URL directly
      2. GitHub user specified: Construct URL from user/branch
      3. Auto-detect: Use VASTAI_GITHUB_USER env var or default to "jiso007"
      
      Args:
          provisioning_script: Either a full URL or just filename (e.g., "test2.sh")
          github_user: GitHub username (optional, falls back to env var/default)
          github_branch: GitHub branch name (default: "main")
      
      Returns:
          str: Full URL to the provisioning script
      
      Examples:
          >>> get_provisioning_script_url("https://raw.github.com/.../script.sh")
          "https://raw.github.com/.../script.sh"  # Returns as-is
          
          >>> get_provisioning_script_url("test2.sh", github_user="jus10wang-stack")
          "https://raw.githubusercontent.com/jus10wang-stack/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/test2.sh"
          
          >>> os.environ["VASTAI_GITHUB_USER"] = "alice"
          >>> get_provisioning_script_url("test.sh")
          "https://raw.githubusercontent.com/alice/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/test.sh"
      """
      # Mode 1: Full URL provided - use it directly
      if provisioning_script.startswith("http://") or provisioning_script.startswith("https://"):
          return provisioning_script

      # Mode 2 & 3: Construct URL from components
      # Handle empty/None github_user - fall back to env var or default
      if not github_user:  # Catches None, empty string, and other falsy values
          github_user = os.getenv("VASTAI_GITHUB_USER", "jiso007")

      # Handle empty/None github_branch - use default
      if not github_branch:
          github_branch = "main"

      # Construct the full URL
      return f"https://raw.githubusercontent.com/{github_user}/vastai/refs/heads/{github_branch}/TEMPLATES/provisioning_script
  s/{provisioning_script}"

  1.2: Update Function Signature

  Change line 14:

  # BEFORE:
  def create_instance(offer_id, provisioning_script="provision_test_3.sh", disk_size=100):

  # AFTER:
  def create_instance(offer_id, provisioning_script="provision_test_3.sh", disk_size=100, github_user=None, 
  github_branch="main"):

  1.3: Update Provisioning Script URL

  Change line 41 (in the API payload):

  # BEFORE:
  "PROVISIONING_SCRIPT":
  f"https://raw.githubusercontent.com/jiso007/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/{provisioning_script}"

  # AFTER:
  "PROVISIONING_SCRIPT": get_provisioning_script_url(provisioning_script, github_user, github_branch)

  ---
  Step 2: Update create_and_monitor_config.py

  Location: SCRIPTS/python_scripts/workflows/create_and_monitor_config.py

  2.1: Update load_instance_config() Function

  Modify the function (lines 24-45) to extract and return GitHub settings:

  def load_instance_config(config_filename, script_dir):
      """Load instance configuration from config file."""
      config_path = os.path.join(script_dir, "TEMPLATES", "configs", config_filename)

      if not os.path.exists(config_path):
          raise FileNotFoundError(f"Config file not found: {config_path}")

      with open(config_path, 'r') as f:
          config = json.load(f)

      instance_config = config.get("instance_config", {})

      if not instance_config:
          raise ValueError("No instance_config section found in config file")

      # Extract required values with defaults
      gpu_name = instance_config.get("gpu_name", "RTX 5090")
      gpu_index = instance_config.get("gpu_index", 0)
      provisioning_script = instance_config.get("provisioning_script", "provision_test_3.sh")
      disk_size = instance_config.get("disk_size", 100)

      # NEW: Extract optional GitHub configuration
      github_user = instance_config.get("github_user", None)
      github_branch = instance_config.get("github_branch", "main")

      # NEW: Return 6 values instead of 4
      return gpu_name, gpu_index, provisioning_script, disk_size, github_user, github_branch

  2.2: Update Caller (line 321)

  # BEFORE:
  gpu_name, gpu_index, provisioning_script, disk_size = load_instance_config(config_filename, script_dir)

  # AFTER:
  gpu_name, gpu_index, provisioning_script, disk_size, github_user, github_branch = load_instance_config(config_filename,
  script_dir)

  2.3: Update create_vast_instance Call (line 343)

  # BEFORE:
  result = create_vast_instance(selected_offer_id, provisioning_script, disk_size)

  # AFTER:
  result = create_vast_instance(selected_offer_id, provisioning_script, disk_size, github_user, github_branch)

  ---
  Step 3: Update oneshot.py

  Location: SCRIPTS/python_scripts/workflows/oneshot.py

  Apply the same changes as Step 2:

  3.1: Update load_instance_config() (around line 26-46)

  - Same as Step 2.1

  3.2: Update Caller (line 364)

  - Same as Step 2.2

  3.3: Update create_vast_instance Call (line 387)

  - Same as Step 2.3

  ---
  Step 4: Update analyze_workflow_generic.py

  Location: SCRIPTS/python_scripts/workflows/analyze_workflow_generic.py

  4.1: Add GitHub Detection Function

  Insert after line 11 (after imports):

  def detect_github_user():
      """
      Auto-detect GitHub username from the current Git repository.
      
      Returns:
          str: GitHub username or None if not detectable
      
      Examples:
          https://github.com/jus10wang-stack/vastai.git → "jus10wang-stack"
          git@github.com:jiso007/vastai.git → "jiso007"
      """
      import subprocess
      import re

      try:
          # Get the remote origin URL
          result = subprocess.run(
              ['git', 'config', '--get', 'remote.origin.url'],
              capture_output=True,
              text=True,
              timeout=5
          )

          if result.returncode != 0:
              return None

          remote_url = result.stdout.strip()

          if not remote_url:
              return None

          # Parse GitHub username from different URL formats
          # Format 1: https://github.com/USERNAME/repo.git
          # Format 2: git@github.com:USERNAME/repo.git
          # Format 3: https://github.com/USERNAME/repo (no .git)

          # Try both HTTPS and SSH formats
          match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$', remote_url)
          if match:
              username = match.group(1)
              print(f"🔍 Detected GitHub user: {username}")
              return username

          # If no match, return None
          print(f"⚠️  Could not detect GitHub user from: {remote_url}")
          return None

      except subprocess.TimeoutExpired:
          print(f"⚠️  Git command timeout - could not detect GitHub user")
          return None
      except FileNotFoundError:
          print(f"ℹ️  Git not found - could not detect GitHub user")
          return None
      except Exception as e:
          print(f"⚠️  Error detecting GitHub user: {e}")
          return None

  4.2: Update format_for_easy_editing() (lines 82-123)

  Add detection call at the beginning:

  def format_for_easy_editing(cleaned_workflow):
      """
      Further format the cleaned workflow to make it super easy to edit.
      Group similar node types and provide clear parameter names.
      """
      workflow_name = cleaned_workflow["workflow_info"]["name"]
      default_provisioning_script = f"{workflow_name}.sh"

      # NEW: Auto-detect GitHub user
      detected_github_user = detect_github_user()

      formatted = {
          "workflow_info": cleaned_workflow["workflow_info"],
          "instance_config": {
              "gpu_name": "RTX 5090",
              "gpu_index": 0,
              "provisioning_script": default_provisioning_script,
              "disk_size": 100,
          },
          "configurable_parameters": {}
      }

      # NEW: Add github_user if detected
      if detected_github_user:
          formatted["instance_config"]["github_user"] = detected_github_user
          formatted["instance_config"]["note"] = "Instance creation settings - auto-detected github_user from current repo"
      else:
          formatted["instance_config"]["note"] = "Instance creation settings - used when creating new instances for this 
  workflow"

      # ... rest of function unchanged ...

  4.3: Update create_user_friendly_template() (lines 125-168)

  Add the same detection logic:

  def create_user_friendly_template(formatted_workflow):
      """
      Create the most user-friendly version possible.
      This extracts just the values users typically want to change.
      """
      workflow_name = formatted_workflow["workflow_info"]["name"]
      default_provisioning_script = f"{workflow_name}.sh"

      # NEW: Auto-detect GitHub user
      detected_github_user = detect_github_user()

      template = {
          "workflow_name": workflow_name,
          "description": "Edit the values below, then use with execute_workflow_config.py",
          "instance_config": {
              "gpu_name": "RTX 5090",
              "gpu_index": 0,
              "provisioning_script": default_provisioning_script,
              "disk_size": 100,
          },
          "parameters": {}
      }

      # NEW: Add github_user if detected
      if detected_github_user:
          template["instance_config"]["github_user"] = detected_github_user
          template["instance_config"]["note"] = "Instance creation settings - auto-detected github_user from current repo"
      else:
          template["instance_config"]["note"] = "Instance creation settings - used when creating new instances for this 
  workflow"

      # ... rest of function unchanged ...

  ---
  Updated Config File Format

  After these changes, generated configs will look like:

  {
    "workflow_name": "test2",
    "description": "Edit the values below, then use with execute_workflow_config.py",
    "instance_config": {
      "gpu_name": "RTX 5090",
      "gpu_index": 0,
      "github_user": "jus10wang-stack",
      "provisioning_script": "test2.sh",
      "disk_size": 103,
      "note": "Instance creation settings - auto-detected github_user from current repo"
    },
    "parameters": {
      ...
    }
  }

  Usage Examples

  Example 1: Auto-Detection (Recommended)

  cd ~/vastai  # Your local repo clone
  vai workflow analyze my-workflow.json
  # Auto-detects github_user from git remote origin

  Example 2: Manual Specification

  Edit the config file manually:

  {
    "instance_config": {
      "github_user": "alice",
      "provisioning_script": "test2.sh"
    }
  }

  Example 3: Full URL Override

  {
    "instance_config": {
      "provisioning_script": "https://raw.githubusercontent.com/bob/vastai/dev/TEMPLATES/2_provisioning_scripts/test2.sh"
    }
  }

  Example 4: Environment Variable

  export VASTAI_GITHUB_USER="charlie"
  vai create my-config.json
  # Uses charlie's repo

  Testing

  Test 1: Verify Auto-Detection

  # Check current Git remote
  git config --get remote.origin.url

  # Should output something like:
  # https://github.com/YOUR_USERNAME/vastai.git

  # Regenerate config
  vai workflow analyze test2.json

  # Check generated config
  cat TEMPLATES/3_configs/test2-user_friendly.json | grep github_user

  # Should show:
  # "github_user": "YOUR_USERNAME",

  Test 2: Verify URL Construction

  # Create instance with config
  vai create test2-user_friendly.json

  # Check instance logs on Vast.ai
  # Provisioning script URL should be:
  # https://raw.githubusercontent.com/YOUR_USERNAME/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/test2.sh

  Test 3: Backwards Compatibility

  # Use old config without github_user field
  vai create old-config.json

  # Should still work, defaulting to VASTAI_GITHUB_USER env var or "jiso007"

  Troubleshooting

  Issue: github_user Not Appearing in Config

  Cause: Git remote not configured or not a Git repository

  Solution:
  1. Check: git remote -v
  2. If empty, add remote: git remote add origin https://github.com/YOUR_USERNAME/vastai.git
  3. Re-run: vai workflow analyze

  Alternative: Manually add to config file

  Issue: Wrong Provisioning Script Downloaded

  Cause: github_user pointing to wrong repo

  Solution:
  1. Check config: cat TEMPLATES/3_configs/your-config.json | grep github_user
  2. Update to correct username
  3. Or use full URL in provisioning_script

  Issue: 404 Error During Provisioning

  Cause: Provisioning script doesn't exist at the constructed URL

  Solution:
  1. Verify script exists in your repo: ls TEMPLATES/2_provisioning_scripts/
  2. Check GitHub repo has the file committed
  3. Verify URL manually: curl -I 
  https://raw.githubusercontent.com/YOUR_USER/vastai/refs/heads/main/TEMPLATES/2_provisioning_scripts/test2.sh

  Migration Guide

  For Existing Configs

  1. Option A: Regenerate (Recommended)
  vai workflow analyze your-workflow.json
  # Overwrites config with auto-detected github_user
  2. Option B: Manual Edit
  Add to existing config:
  {
    "instance_config": {
      "github_user": "YOUR_USERNAME",
      ...
    }
  }

  For Different Forks

  If collaborating across forks:

  1. Each user regenerates configs in their fork
  2. Or use environment variable approach:
  export VASTAI_GITHUB_USER="your_username"
  3. Add to .env or shell profile for persistence

  Benefits

  ✅ Multi-user support - Different users can use their own forks✅ No hardcoding - GitHub username configurable
  per-workflow✅ Backwards compatible - Old configs still work✅ Auto-detection - Minimal manual configuration needed✅
  Flexible - Supports URLs, configs, env vars, defaults✅ Self-documenting - Config shows which repo is used

  Related Files

  - SCRIPTS/python_scripts/components/create_instance.py
  - SCRIPTS/python_scripts/workflows/create_and_monitor_config.py
  - SCRIPTS/python_scripts/workflows/oneshot.py
  - SCRIPTS/python_scripts/workflows/analyze_workflow_generic.py
  - TEMPLATES/3_configs/*.json (all config files)

  Version History

  - v1.0 - Initial implementation (2025-01-02)
    - Added github_user config field
    - Auto-detection in workflow analyzer
    - Three-level priority system
    - Backwards compatibility maintained