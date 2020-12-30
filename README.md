# rt2zammad

Request tracker to Zammad migration script. This is not an out of box solution
for everybody, you will probably have to customize it.

## Known issues

* Disabled users from RT can not be accessed by API, thus will lack email
  address and will fail to be created. Enable all users prior to the migration.
* Timestamps are not preserved. The Zammad API doesn't seem to allow this.
* Zammad will send notification for all actions, you probably want to disable
  outgoing mail for time of import:
  * Disable all triggers sending mail (Manage / Trigger
  * Disable notifications for all existing users (seems like every user has to do this)
  * Safer approach might be to use own SMTP server and temporarily discard all
    mail from Zammad for the migration run.

## Maintenance status

No further development is expected there. This was used once to migrate
[Weblate](https://weblate.org/) and I have no intent to improve this script
myself. Pull requests are still welcome though.

## Usage

1. Prepare virtualenv and install dependencies: `virtualenv .venv --python python 3; . .venv/bin/activate ; pip install -r requirements.txt`
2. Start `rt2zammad.py`, it will display template for configuration file.
3. Fill in the template and save it as `rt2zammad.json`.
4. Start `rt2zammad.py` to perform the migration.
5. Verify the migration results.
6. In case you need to roll back Zammad, please follow https://community.zammad.org/t/reset-database-to-start-from-zero/326
