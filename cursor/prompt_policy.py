"""Local prompt risk signals and intent-preserving, read-only rewrites."""
import re

SECRET = re.compile(
    r"(?<![\w.])\.env(?:\b|(?=\.))|\b(?:api[ _-]?keys?|tokens?|credentials?|passwords?|secrets?)\b"
    r"|\bprintenv\b|\benv:|(?:^|[/\\])(?:\.npmrc|\.netrc|\.ssh|\.aws|id_rsa|id_ed25519)(?:$|[/\\])",
    re.I,
)
DESTRUCTIVE = re.compile(
    r"\b(?:delete|remove|erase|wipe|destroy|truncate)\b|\brm\s+-|\bremove-item\b|\bdrop\s+(?:table|database)\b", re.I
)
DISCLOSURE = re.compile(r"\b(?:fetch|dump|print|reveal|show|send|upload|extract|display|expose|read|copy)\b", re.I)
GIT = re.compile(r"\bgit\s+(?:push|reset\s+--hard|clean\s+-)|\bforce[- ]push\b|\brewrite\b.{0,35}\bhistory\b", re.I)
EXTERNAL = re.compile(r"\b(?:send|publish|upload|deploy|roll out)\b|"
                      r"(?:^|\b(?:and|then)\s+)(?:please\s+)?(?:email|post|release)\b", re.I)
INFRA = re.compile(r"\b(?:restart|reboot|disable|grant|revoke|migrate)\b", re.I)
CLEANUP = re.compile(r"\bgenerated (?:files|artifacts)\b|\b(?:old )?build outputs?\b"
                     r"|\b(?:unused )?(?:temporary|temp) files\b|\b(?:stale )?caches?\b", re.I)
READ_ONLY = re.compile(r"^(?:please\s+)?(?:find|list|inspect|analy[sz]e|explain|identify|"
                       r"summari[sz]e|describe|give|compare|check|walk|document|draft|plan|review|show)\b", re.I)
MAY_MUTATE = re.compile(r"\b(?:run|execute|overwrite|rename|move|write|install|apply|replace|modify|enable|create|edit)\b", re.I)
VALUE = re.compile(r"\b[\w.-]+\s*=\s*\S+|https?://|[A-Za-z0-9_+/=-]{24,}|\b(?:Bearer|Basic)\s+\S+|[\x00-\x08\x0b\x0c\x0e-\x1f]")
FILE = re.compile(r"(?<![\w./\\])[A-Za-z0-9_-][A-Za-z0-9_./-]{0,100}\.(?:txt|md|csv|json|log|py|js|ts|html|css)\b", re.I)
CLAUSES = re.compile(
    r"[\n;]+|(?<=[.!?])\s+|,\s*(?=(?:and\s+)?(?:please\s+)?(?:"
    r"find|list|inspect|analy[sz]e|explain|identify|summari[sz]e|describe|"
    r"delete|remove|erase|wipe|destroy|fetch|reveal|upload|deploy|send|run|execute)\b)"
    r"|\s+(?:and|then)\s+(?=(?:delete|remove|erase|wipe|destroy|truncate|fetch|reveal|"
    r"upload|expose|run|execute|install|overwrite|write|send|copy|move|rename|push|publish|"
    r"deploy|restart|list|explain|identify|summari[sz]e|inspect|describe|draft)\b)", re.I
)


def prompt_category(text):
    if SECRET.search(text) and (DESTRUCTIVE.search(text) or DISCLOSURE.search(text)):
        return "secret-destructive"
    if GIT.search(text):
        return "git-risk"
    if DESTRUCTIVE.search(text):
        return "destructive"
    if EXTERNAL.search(text):
        return "external-action"
    if INFRA.search(text):
        return "system-change"
    return "ordinary"


def _safe_targets(text):
    return [target for target in FILE.findall(text)
            if not SECRET.search(target) and not VALUE.search(target)
            and not any(part in {".", ".."} for part in target.split("/"))]


def refine_prompt(prompt):
    """Preserve recognizable read-only clauses and turn consequential steps into plans."""
    parts = []
    category = prompt_category(prompt)
    for raw in CLAUSES.split(prompt):
        clause = raw.strip(" ,")
        if (len(clause) <= 280 and READ_ONLY.match(clause) and prompt_category(clause) == "ordinary"
                and not SECRET.search(clause) and not VALUE.search(clause)
                and not MAY_MUTATE.search(clause) and not any(c in clause for c in "`|<>")):
            parts.append(clause)

    cleanup = list(dict.fromkeys(match.group().lower() for match in CLEANUP.finditer(prompt)))
    if cleanup:
        parts.insert(0, "Analyze the repository for cleanup candidates, including " + ", ".join(cleanup))
    elif DESTRUCTIVE.search(prompt) and not GIT.search(prompt):
        targets = _safe_targets(prompt)
        if targets:
            parts.insert(0, "Inspect these items and explain whether each is a cleanup candidate: "
                         + ", ".join(dict.fromkeys(targets)))
        elif re.search(r"\b(?:clean\s*up|cleanup)\b", prompt, re.I):
            parts.insert(0, "Analyze the repository and list cleanup candidates with reasons")
        elif re.search(r"\b(?:table|database|rows|records)\b", prompt, re.I):
            parts.append("Give a read-only assessment of the affected data, dependencies, and recovery options")

    if GIT.search(prompt):
        parts.append("Inspect the current branch and commit history. Describe the proposed Git changes and recovery options")
    if EXTERNAL.search(prompt):
        if re.search(r"\b(?:deploy|release|roll out)\b", prompt, re.I):
            environment = re.search(r"\b(?:production|staging|sandbox|development|test)\b", prompt, re.I)
            target = f" for {environment.group().lower()}" if environment else ""
            parts.append(f"Prepare a rollout checklist{target} covering validation, impact, and rollback")
        else:
            parts.append("Prepare a draft for my approval and describe the intended audience and destination")
    if INFRA.search(prompt):
        parts.append("Describe the proposed system change, prerequisites, likely impact, and rollback")
    if category == "secret-destructive":
        parts.append("Leave sensitive configuration untouched and omit its values")
    if not parts:
        parts.append("Outline a read-only plan for the requested work and ask me to clarify the scope")
    parts.append("Leave the workspace unchanged and wait for my confirmation before making changes")
    return " ".join(part.rstrip(".?!") + "." for part in dict.fromkeys(parts))
