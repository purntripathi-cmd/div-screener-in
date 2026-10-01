import os
import sys
import argparse
import subprocess
from pathlib import Path

SPACE_NAME = "PurnT/Screener"
HF_SPACE_URL = f"https://huggingface.co/spaces/{SPACE_NAME}"

WORKSPACE_PATHS = {
    "production": Path(r"C:\Users\epurntr\.gemini\antigravity\brain\f3b08972-3bf1-4386-ae3d-574c8ac8be88\scratch\smart-etf-tracker"),
    "div_screener": Path(r"C:\Users\epurntr\.gemini\antigravity\brain\f3b08972-3bf1-4386-ae3d-574c8ac8be88\scratch\div-screener-in"),
    "gravity": Path(r"C:\Users\epurntr\Downloads\Gravity")
}

def load_token_from_env():
    """
    Safely retrieves Hugging Face token without printing it.
    Checks environment variables and ~/.env or ./.env files.
    """
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_TOKEN")
    if token and token.strip():
        return token.strip()

    candidate_files = [
        Path.home() / ".env",
        Path.cwd() / ".env",
        Path(r"C:\Users\epurntr\Downloads\Gravity\.env")
    ]

    for p in candidate_files:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("HF_TOKEN="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
                        elif line.startswith("HUGGING_FACE_TOKEN="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass

    return None

def sanitize_output(text, token):
    if token and token in text:
        return text.replace(token, "***TOKEN***")
    return text

def sync_repository(repo_path, token, force=True):
    """
    Pushes repository to Hugging Face Spaces.
    """
    if not repo_path.exists():
        print(f"[!] Target directory does not exist: {repo_path}")
        return False

    auth_url = f"https://PurnT:{token}@huggingface.co/spaces/{SPACE_NAME}"

    print(f"\n[*] Preparing repository at: {repo_path}")
    print(f"[*] Target Hugging Face Space: {HF_SPACE_URL}")

    # Configure remote
    cmd_set_url = ["git", "remote", "set-url", "hf", auth_url]
    p = subprocess.run(cmd_set_url, cwd=repo_path, capture_output=True, text=True)
    if p.returncode != 0:
        cmd_add_remote = ["git", "remote", "add", "hf", auth_url]
        subprocess.run(cmd_add_remote, cwd=repo_path, capture_output=True, text=True)

    print(f"[*] Executing push to Hugging Face main branch...")
    push_args = ["git", "push", "hf", "main:main"]
    if force:
        push_args.append("--force")

    result = subprocess.run(push_args, cwd=repo_path, capture_output=True, text=True)

    # Sanitize and reset remote url to remove embedded token
    clean_url = f"https://huggingface.co/spaces/{SPACE_NAME}"
    subprocess.run(["git", "remote", "set-url", "hf", clean_url], cwd=repo_path, capture_output=True)

    stdout_clean = sanitize_output(result.stdout, token)
    stderr_clean = sanitize_output(result.stderr, token)

    if result.returncode == 0:
        print("\n" + "="*70)
        print("  SUCCESSFULLY SYNCED TO HUGGING FACE SPACES!")
        print("="*70)
        print(f"  Live Space URL: {HF_SPACE_URL}")
        print("  Hugging Face is building and launching your Streamlit container.")
        print("="*70)
        if stdout_clean.strip():
            print(f"Git Output:\n{stdout_clean}")
        if stderr_clean.strip():
            print(f"Git Info:\n{stderr_clean}")
        return True
    else:
        print("\n[!] Push failed:")
        if stderr_clean.strip():
            print(stderr_clean)
        elif stdout_clean.strip():
            print(stdout_clean)
        return False

def main():
    parser = argparse.ArgumentParser(description="Sync application to Hugging Face Space PurnT/Screener")
    parser.add_argument("--target", choices=["production", "div_screener"], default="production", help="Choose which codebase to sync")
    parser.add_argument("--token", default=None, help="Hugging Face User Access Token (optional if set in HF_TOKEN env var)")
    parser.add_argument("--save-token", action="store_true", help="Save the provided token to ~/.env for future automated syncs")

    args = parser.parse_args()

    token = args.token or load_token_from_env()

    if not token:
        print("="*70)
        print("  HUGGING FACE AUTHENTICATION TOKEN REQUIRED")
        print("="*70)
        print("To push to your Space (https://huggingface.co/spaces/PurnT/Screener),")
        print("a Hugging Face User Access Token with 'Write' permissions is needed.\n")
        print("1. Obtain or generate your token here:")
        print("   -> https://huggingface.co/settings/tokens")
        print("   (Click 'New token' -> Name: 'Gravity-Sync' -> Type: 'Write' -> Generate)\n")
        print("2. Run one of the following commands:")
        print("   PowerShell (Safe - typing hidden):")
        print('     $t = Read-Host -Prompt "Enter HF Token" -AsSecureString; $p = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($t)); [System.IO.File]::AppendAllText("$env:USERPROFILE\\.env", "`nHF_TOKEN=$p`n"); python sync_to_huggingface.py\n')
        print("   Or run directly with the token:")
        print("     python sync_to_huggingface.py --token <YOUR_HF_TOKEN> --save-token\n")
        print("="*70)
        return 1

    if args.save_token and args.token:
        env_path = Path.home() / ".env"
        try:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write(f"\nHF_TOKEN={args.token.strip()}\n")
            print(f"[*] Successfully saved token to {env_path}")
        except Exception as e:
            print(f"[!] Could not save token: {e}")

    repo_dir = WORKSPACE_PATHS.get(args.target)
    if not repo_dir or not repo_dir.exists():
        repo_dir = WORKSPACE_PATHS["gravity"]

    success = sync_repository(repo_dir, token)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
