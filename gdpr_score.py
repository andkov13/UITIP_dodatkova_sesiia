
def calculate_gdpr_score(audit):
    score = 100
    if not audit["localized_page_found"]:
        score -= 20
    if not audit["cookie_banner"]:
        score -= 25
    if not audit["privacy_policy_found"]:
        score -= 30
    elif not audit["privacy_mentions_data"]:
        score -= 10
    if not audit["cookie_policy_found"]:
        score -= 15
    elif not audit["cookie_policy_detailed"]:
        score -= 5
    return max(score, 0)

def estimate_fine(score):
    if score == 100:
        return "No risk of GDPR fines."
    elif score >= 80:
        return "Low risk of GDPR fines."
    elif score >= 50:
        return "Moderate risk of GDPR fines."
    else:
        return "High risk of GDPR fines. Immediate action recommended."
