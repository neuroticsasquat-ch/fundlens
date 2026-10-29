#!/usr/bin/env bash
# Creates the long-lived updates/dependencies branch and the repository's three rulesets, or
# brings them back in line with this file. The rulesets are the NS-repo standard, copied from
# tvbf-backend, plus the required CI check on main.
#
#   scripts/github-rulesets.sh [owner/repo]     # default: neuroticsasquat-ch/fundlens
#
# Idempotent: each ruleset is matched by name, and a run that finds everything as declared here
# prints "unchanged" for each and changes nothing. Edit a ruleset here, not in the GitHub UI;
# the next run overwrites UI edits. Runs on the host (it needs your `gh` login and jq) and needs
# admin on the repo.
#
# main deliberately has no "require linear history" rule: PRs into main land as merge commits
# (allowed_merge_methods below, and how /mergeit merges), and updates/dependencies reaches main
# as a merge so that main stays its ancestor; linear history would reject both.
set -euo pipefail

REPO="${1:-neuroticsasquat-ch/fundlens}"
DEPS_BRANCH="updates/dependencies"
# The `test` job in .github/workflows/ci.yml; 15368 is the GitHub Actions app, so only a run of
# that workflow can satisfy the check.
CI_CHECK="test"
ACTIONS_APP_ID=15368

# The fields a ruleset GET returns that this script manages, so a GET can be compared with a body.
FIELDS='{name, target, enforcement, conditions, bypass_actors, rules}'

# The pull_request rule's parameters with GitHub's defaults spelled out: a GET returns all of
# them, and leaving any out would make every run see a difference and report "updated".
pull_request_rule() {
  jq -n --argjson methods "$1" '{
    type: "pull_request",
    parameters: {
      allowed_merge_methods: $methods,
      dismiss_stale_reviews_on_push: false,
      dismissal_restriction: {allowed_actors: [], enabled: false},
      require_code_owner_review: false,
      require_extra_approval_for_unattributed_changes: true,
      require_last_push_approval: false,
      required_approving_review_count: 0,
      required_review_thread_resolution: false,
      required_reviewers: []
    }
  }'
}

ruleset() {
  local name="$1" include="$2" rules="$3"
  jq -n --arg name "$name" --argjson include "$include" --argjson rules "$rules" '{
    name: $name,
    target: "branch",
    enforcement: "active",
    conditions: {ref_name: {include: $include, exclude: []}},
    bypass_actors: [],
    rules: $rules
  }'
}

ensure_deps_branch() {
  # Before the rulesets: once the integration-branch rules exist they block pushing the branch.
  if gh api "repos/$REPO/git/ref/heads/$DEPS_BRANCH" >/dev/null 2>&1; then
    echo "branch $DEPS_BRANCH: unchanged"
    return
  fi
  local sha
  sha=$(gh api "repos/$REPO/git/ref/heads/main" --jq .object.sha)
  gh api -X POST "repos/$REPO/git/refs" -f ref="refs/heads/$DEPS_BRANCH" -f sha="$sha" >/dev/null
  echo "branch $DEPS_BRANCH: created from main ($sha)"
}

apply_ruleset() {
  local body="$1" name id current
  name=$(jq -r .name <<<"$body")
  id=$(gh api "repos/$REPO/rulesets?per_page=100" \
    | jq -r --arg name "$name" '.[] | select(.source_type == "Repository" and .name == $name) | .id')

  if [[ -z "$id" ]]; then
    gh api -X POST "repos/$REPO/rulesets" --input - <<<"$body" >/dev/null
    echo "ruleset '$name': created"
    return
  fi

  current=$(gh api "repos/$REPO/rulesets/$id" | jq "$FIELDS")
  if [[ "$(jq -S . <<<"$current")" == "$(jq -S . <<<"$body")" ]]; then
    echo "ruleset '$name': unchanged"
  else
    gh api -X PUT "repos/$REPO/rulesets/$id" --input - <<<"$body" >/dev/null
    echo "ruleset '$name': updated"
  fi
}

ensure_deps_branch

apply_ruleset "$(ruleset "main" '["~DEFAULT_BRANCH"]' "$(jq -n \
  --argjson pr "$(pull_request_rule '["merge"]')" \
  --arg check "$CI_CHECK" --argjson app "$ACTIONS_APP_ID" '[
    {type: "deletion"},
    {type: "non_fast_forward"},
    $pr,
    {
      type: "required_status_checks",
      parameters: {
        do_not_enforce_on_create: false,
        required_status_checks: [{context: $check, integration_id: $app}],
        strict_required_status_checks_policy: false
      }
    }
  ]')")"

apply_ruleset "$(ruleset "Integration branches — shared rules" \
  '["refs/heads/updates/*", "refs/heads/release/*"]' \
  "$(jq -n --argjson pr "$(pull_request_rule '["squash", "merge"]')" \
    '[{type: "non_fast_forward"}, $pr]')")"

apply_ruleset "$(ruleset "Protect updates branches from deletion" \
  '["refs/heads/updates/*"]' '[{"type": "deletion"}]')"
