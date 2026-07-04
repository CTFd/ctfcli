from ctfcli.utils.integrations.github import create_github_integration
from ctfcli.utils.integrations.gitlab import create_gitlab_integration

# name -> (human label, creator). Add a future provider here + one switch in init().
INTEGRATIONS = {
    "github": ("GitHub Actions", create_github_integration),
    "gitlab": ("GitLab CI/CD", create_gitlab_integration),
}
