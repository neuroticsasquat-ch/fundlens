from fundlens.settings import Settings

# docker-compose.yml bind-mounts the whole repo at /app, so a developer's `.env` sits exactly
# where pydantic-settings looks for it. A test that clears a variable to assert a default, or
# the required-field error, would read the value straight back out of that file. The process
# environment is the only source a test should see.
Settings.model_config["env_file"] = None
