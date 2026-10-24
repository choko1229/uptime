SESSION_COOKIE_NAME = "uptime_session"
DEFAULT_SITE_TITLE = "Uptime Monitor"

# The `PORT` environment variable is the only thing configured via .env / the
# shell environment (see Dockerfile CMD). Everything else - database
# connection, admin account, SMTP, PageSpeed key, site title - is configured
# through the app itself: DB connection via /setup on first boot, the rest
# via /admin/settings once logged in.
