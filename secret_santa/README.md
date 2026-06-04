# Secret Santa Draw Script

Runs the Secret Santa draw for the 65€ Budget Commander Challenge. Each participant gets a private, expiring link (via [Password Pusher](https://eu.pwpush.com)) revealing who they are challenging.

## Setup

**1. Create and activate the virtual environment**

```bash
cd secret_santa/
python3 -m venv .venv
source .venv/bin/activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure credentials**

Copy the example env file and fill in your [Password Pusher API credentials](https://eu.pwpush.com/users/sign_up):

```bash
cp .env.example .env
```

Edit `.env`:

```
PWPUSH_EMAIL=you@example.com
PWPUSH_TOKEN=your_api_token_here
```

**4. Set participants**

Edit `config.json`:

```json
{
  "challenge": "budget-2026",
  "participants": [
    "Alice",
    "Bob",
    "Charlie"
  ]
}
```

The `challenge` value is used as the results filename (`results_budget-2026.md`).

**5. Customize the message (optional)**

Edit `template.json` to change the upper and lower text around the recipient reveal. Available placeholders:

| Placeholder | Value |
|-------------|-------|
| `{attendee}` | Name of the person receiving the link |
| `{number}` | Position number of their assigned challenger on the roster |

## Usage

```bash
source .venv/bin/activate   # if not already active
python secret_santa.py
```

The script will:

1. Run the draw (Sattolo's algorithm — guaranteed no self-assignments)
2. Create one private link per participant via eu.pwpush.com (expires after **7 days or 3 views**)
3. Print the results table to stdout
4. Write `results/results_<challenge>.md`

**Send each person only their own link.** The links are private — opening someone else's link reveals who they have to challenge.

## Output example

```
Secret Santa Draw — budget-2026
================================
  #  Attendee   Link
  —  ————————   ————————————————————————————————————
  1  Alice      https://eu.pwpush.com/p/abc123
  2  Bob        https://eu.pwpush.com/p/def456
  3  Charlie    https://eu.pwpush.com/p/ghi789
```

A Markdown version is saved to `results/results_budget-2026.md`.

## Files

```
secret_santa/
├── secret_santa.py     — main script
├── config.json         — challenge name + participant list
├── template.json       — message template (upper/lower parts)
├── requirements.txt    — Python dependencies
├── .env.example        — credential template
├── .env                — your credentials (gitignored)
├── .venv/              — virtual environment (gitignored)
└── results/            — output files (gitignored)
```
