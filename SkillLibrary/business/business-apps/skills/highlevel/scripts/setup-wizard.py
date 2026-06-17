#!/usr/bin/env python3
"""GoHighLevel Setup Wizard — Interactive onboarding for new users.

Usage: python3 setup-wizard.py

Walks through:
  1. Check if HIGHLEVEL_TOKEN and HIGHLEVEL_LOCATION_ID are set
  2. Guide user through Private Integration creation (correct 2025-2026 method)
  3. Test the connection
  4. Pull first 5 contacts as a quick win
"""

import json, os, sys, urllib.request, urllib.error

BASE = "https://services.leadconnectorhq.com"
VERSION = "2021-07-28"

# ── Colors for terminal output ──────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def p(msg, color="", **kwargs):
    """Print with optional color."""
    print(f"{color}{msg}{RESET}", **kwargs)


def header(title):
    p(f"\n{'─' * 50}", CYAN)
    p(f"  {title}", BOLD)
    p(f"{'─' * 50}", CYAN)


def check_mark():
    return f"{GREEN}✓{RESET}"


def x_mark():
    return f"{RED}✗{RESET}"


def api_request(token, path):
    """Make a GET request to the GHL API."""
    url = f"{BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Version": VERSION,
        "Accept": "application/json",
        "User-Agent": "OpenClaw-GHL-Skill/1.1.0",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode() if e.fp else ""
        except Exception:
            pass
        return None, f"HTTP {e.code}: {body[:200]}"
    except Exception as ex:
        return None, str(ex)


def step1_check_env():
    """Check if environment variables are already set."""
    header("Step 1: Checking Environment Variables")

    token = os.environ.get("HIGHLEVEL_TOKEN", "").strip()
    loc_id = os.environ.get("HIGHLEVEL_LOCATION_ID", "").strip()

    token_ok = bool(token)
    loc_ok = bool(loc_id)

    if token_ok:
        masked = token[:8] + "..." + token[-4:] if len(token) > 12 else "***"
        p(f"  {check_mark()} HIGHLEVEL_TOKEN is set ({masked})")
    else:
        p(f"  {x_mark()} HIGHLEVEL_TOKEN is NOT set")

    if loc_ok:
        p(f"  {check_mark()} HIGHLEVEL_LOCATION_ID is set ({loc_id})")
    else:
        p(f"  {x_mark()} HIGHLEVEL_LOCATION_ID is NOT set")

    return token, loc_id, token_ok, loc_ok


def step2_guide_setup(token_ok, loc_ok):
    """Guide user through getting their token and location ID - with interactive input."""
    if token_ok and loc_ok:
        p(f"\n  {check_mark()} Both variables are set! Skipping to connection test.", GREEN)
        return None, None

    header("Step 2: Setting Up Your Private Integration")

    # If token not set, show instructions then prompt
    if not token_ok:
        p(f"""
  {BOLD}How to get your Private Integration token:{RESET}

  1. Log into {CYAN}app.gohighlevel.com{RESET}
  2. Switch to your {BOLD}Sub-Account{RESET} (recommended for single-location use)
  3. Click {BOLD}Settings{RESET} (bottom-left gear icon)
  4. Select {BOLD}Private Integrations{RESET} in the left sidebar
     {YELLOW}→ Not visible? Enable it: Settings → Labs → toggle ON{RESET}
  5. Click {BOLD}"Create new Integration"{RESET}
  6. Name it (e.g., "Claude AI Assistant")
  7. Select only the scopes you need (e.g., contacts, conversations, calendars)
     {YELLOW}→ Start minimal — you can add more scopes later without regenerating the token{RESET}
  8. Click Create → {RED}COPY THE TOKEN IMMEDIATELY{RESET}
     {YELLOW}→ It is shown ONLY ONCE and cannot be retrieved later!{RESET}

  {BOLD}⚠️  DO NOT use Settings → API Keys — that's the old V1 method (deprecated){RESET}
""")
        token = input(f"{CYAN}  Enter your Private Integration token: {RESET}").strip()
        os.environ["HIGHLEVEL_TOKEN"] = token
        token_ok = bool(token)

    # If location ID not set, show instructions then prompt
    if not loc_ok:
        p(f"""
  {BOLD}How to find your Location ID:{RESET}

  {BOLD}Method 1 — URL bar:{RESET}
  While in your sub-account, check the browser URL:
  {CYAN}app.gohighlevel.com/v2/location/{YELLOW}THIS-IS-YOUR-LOCATION-ID{CYAN}/...{RESET}

  {BOLD}Method 2 — Business Profile:{RESET}
  Sub-account → {BOLD}Settings{RESET} → {BOLD}Business Info{RESET} (or Business Profile)
  → Location ID is in the General Information section
""")
        loc_id = input(f"{CYAN}  Enter your Location ID: {RESET}").strip()
        os.environ["HIGHLEVEL_LOCATION_ID"] = loc_id
        loc_ok = bool(loc_id)

    if token_ok and loc_ok:
        p(f"\n  {check_mark()} Credentials captured! Moving to connection test...", GREEN)

    return os.environ.get("HIGHLEVEL_TOKEN", ""), os.environ.get("HIGHLEVEL_LOCATION_ID", "")


def step3_test_connection(token, loc_id):
    """Test the API connection."""
    header("Step 3: Testing Connection")

    p("  Connecting to GoHighLevel API v2...")
    p(f"  Base URL: {CYAN}{BASE}{RESET}")
    p(f"  Version:  {CYAN}{VERSION}{RESET}")
    print()

    # Test: Token + Location validity
    p("  Testing token...", end="")
    data, err = api_request(token, f"/locations/{loc_id}")

    if err:
        p(f" {x_mark()}")
        print()
        if "401" in str(err):
            p("  ❌ Authentication failed — your token is invalid or expired.", RED)
            p("  Fix: Go to Settings → Private Integrations → create a new one")
            p("  or rotate your existing token.")
        elif "403" in str(err):
            p("  ❌ Permission denied — your token is missing required scopes.", RED)
            p("  Fix: Edit your Private Integration → add the needed scopes.")
            p("  (You can add scopes without regenerating the token)")
        elif "404" in str(err):
            p("  ❌ Location not found — your HIGHLEVEL_LOCATION_ID is wrong.", RED)
            p("  Fix: Check the URL bar in your sub-account or Settings → Business Info")
        elif "422" in str(err):
            p("  ❌ Invalid request — check your Location ID format.", RED)
        else:
            p(f"  ❌ Unexpected error: {err}", RED)
        return False

    p(f" {check_mark()}")

    # Extract location info
    loc = data.get("location", data)
    name = loc.get("name", "Unknown")
    address = loc.get("address", "")
    tz = loc.get("timezone", "")
    phone = loc.get("phone", "")
    email = loc.get("email", "")

    print()
    p(f"  {check_mark()} {GREEN}Connected successfully!{RESET}")
    print()
    p(f"  {BOLD}Location:{RESET}  {name}")
    if address:
        p(f"  {BOLD}Address:{RESET}   {address}")
    if tz:
        p(f"  {BOLD}Timezone:{RESET}  {tz}")
    if phone:
        p(f"  {BOLD}Phone:{RESET}     {phone}")
    if email:
        p(f"  {BOLD}Email:{RESET}     {email}")

    return True


def step4_quick_win(token, loc_id):
    """Pull first 5 contacts as a quick win to show it works."""
    header("Step 4: Quick Win — Your First 5 Contacts")

    p("  Fetching contacts...")
    params = f"locationId={loc_id}&limit=5"
    data, err = api_request(token, f"/contacts/?{params}")

    if err:
        p(f"  {x_mark()} Could not fetch contacts: {err}", RED)
        if "403" in str(err):
            p("  Your token may be missing the 'contacts.readonly' scope.", YELLOW)
            p("  Edit your Private Integration to add it.")
        return

    contacts = data.get("contacts", [])
    total = data.get("total", data.get("meta", {}).get("total", len(contacts)))

    if not contacts:
        p(f"  No contacts found yet. This sub-account might be empty.", YELLOW)
        p(f"  Try creating a test contact in GHL or via the API.")
        return

    print()
    p(f"  {GREEN}Found {total} total contacts. Here are the first {len(contacts)}:{RESET}")
    print()

    for i, c in enumerate(contacts, 1):
        name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() or "No Name"
        email = c.get("email", "—")
        phone = c.get("phone", "—")
        tags = ", ".join(c.get("tags", [])) if c.get("tags") else "—"
        p(f"  {BOLD}{i}.{RESET} {name}")
        p(f"     Email: {email}")
        p(f"     Phone: {phone}")
        p(f"     Tags:  {tags}")
        print()


def print_next_steps():
    """Show what the user can do next."""
    header("🎉 Setup Complete!")
    p(f"""
  You're all set! Here's what you can do now:

  {BOLD}Ask Claude things like:{RESET}
  • "Search my contacts for John"
  • "Show me my upcoming appointments"
  • "List my pipeline opportunities"
  • "Send an SMS to [contact] saying..."
  • "Create a new contact for Jane Doe at jane@example.com"
  • "What workflows do I have?"
  • "Show me my recent invoices"

  {BOLD}Helper script commands:{RESET}
  {CYAN}python3 scripts/ghl-api.py search_contacts "john"
  python3 scripts/ghl-api.py list_calendars
  python3 scripts/ghl-api.py list_opportunities
  python3 scripts/ghl-api.py list_workflows{RESET}

  {BOLD}─── Connect with us ───{RESET}
  🌐  {CYAN}https://launchmyopenclaw.com{RESET}
  🌐  {CYAN}https://myfbleads.com{RESET}
  ▶️   {CYAN}https://youtube.com/@10xcoldleads{RESET}
  📘  {CYAN}https://facebook.com/ty.shane.howell.2025{RESET}
  💼  {CYAN}https://linkedin.com/in/ty-shane/{RESET}
  📧  ty@10xcoldleads.com

  {BOLD}Don't have GoHighLevel yet?{RESET}
  Start with the free 5-Day AI Employee Challenge:
  👉  {CYAN}https://gohighlevel.com/5-day-challenge?fp_ref=369ai{RESET}
""")


def main():
    p(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════╗
║        GoHighLevel API — Setup Wizard            ║
║        by Ty Shane · @10xcoldleads               ║
║        launchmyopenclaw.com · myfbleads.com      ║
╚══════════════════════════════════════════════════╝{RESET}
""")

    # Step 1: Check environment
    token, loc_id, token_ok, loc_ok = step1_check_env()

    # Step 2: Guide setup if needed (interactive)
    if not token_ok or not loc_ok:
        token, loc_id = step2_guide_setup(token_ok, loc_ok)
        if token and loc_id:
            token_ok = True
            loc_ok = True
        else:
            p("\n  Missing required credentials. Exiting.", RED)
            sys.exit(1)

    # Step 3: Test connection
    connected = step3_test_connection(token, loc_id)
    if not connected:
        print()
        p("  Fix the issue above and run this wizard again.", YELLOW)
        sys.exit(1)

    # Step 4: Quick win
    step4_quick_win(token, loc_id)

    # Done!
    print_next_steps()


if __name__ == "__main__":
    main()
