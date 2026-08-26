import subprocess
import json


def _run_gh_command(cmd: list):
    """Run a GitHub CLI command safely."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}


def _calculate_risk(files_changed, additions, deletions, reviews_count=0):
    """Advanced heuristic risk scoring."""
    risk_score = 0
    flags = []

    # File change risk
    if files_changed > 20:
        risk_score += 40
        flags.append("LARGE_FILE_CHANGE")
    elif files_changed > 10:
        risk_score += 25
    else:
        risk_score += 10

    # Code churn risk
    churn = additions + deletions
    if churn > 1000:
        risk_score += 40
        flags.append("HIGH_CODE_CHURN")
    elif churn > 300:
        risk_score += 25
    else:
        risk_score += 10

    # Review risk
    if reviews_count == 0:
        risk_score += 20
        flags.append("NO_REVIEWS")
    elif reviews_count < 2:
        risk_score += 10

    # Normalize
    risk_score = min(risk_score, 100)

    # Risk level
    if risk_score >= 80:
        level = "HIGH"
        recommendation = "BLOCK AND REQUIRE DEEP REVIEW"
    elif risk_score >= 50:
        level = "MEDIUM"
        recommendation = "REQUIRE SENIOR REVIEW"
    else:
        level = "LOW"
        recommendation = "MERGE WITH BASIC REVIEW"

    confidence = round(0.6 + (risk_score / 250), 2)

    return risk_score, level, recommendation, confidence, flags


def analyze_pr_risk(pr_number: int, repo: str = "getbindu/bindu"):
    """
    Analyze PR risk using REAL GitHub data.

    NOTE: Uses only public GitHub PR metadata.
    No private or confidential data is accessed.
    """

    # Fetch PR metadata
    pr_data = _run_gh_command([
        "gh", "pr", "view", str(pr_number),
        "--repo", repo,
        "--json", "title,additions,deletions,changedFiles,reviews"
    ])

    if "error" in pr_data:
        return {
            "error": "Failed to fetch PR data",
            "details": pr_data["error"]
        }

    try:
        title = pr_data.get("title", "")
        additions = pr_data.get("additions", 0)
        deletions = pr_data.get("deletions", 0)
        files_changed = pr_data.get("changedFiles", 0)
        reviews_count = len(pr_data.get("reviews", []))

        risk_score, level, recommendation, confidence, flags = _calculate_risk(
            files_changed,
            additions,
            deletions,
            reviews_count
        )

        return {
            "pr_number": pr_number,
            "title": title,
            "risk_score": risk_score,
            "risk_level": level,
            "confidence": confidence,
            "recommendation": recommendation,
            "flags": flags,
            "metrics": {
                "files_changed": files_changed,
                "additions": additions,
                "deletions": deletions,
                "reviews": reviews_count
            }
        }

    except Exception as e:
        return {
            "error": "Processing failure",
            "details": str(e)
        }