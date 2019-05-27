# rt2zammad

Request tracker to Zammad migration script. This is not an out of box solution
for everybody, you will probably have to customize it.

Known issues:

* Comments on issues from non creators are rejected by Zammad. This can be
  workarounded by creating appropriate organizations in Zammad manually or
  temporarily grainting Users group agent privilege.
* Disabled users from RT can not be accessed by API, thus will lack email
  address and will fail to be created. Enable all users prior to the migration.
* Timestamps are not preserved. The Zammad API doesn't seem to allow this.
