from pathlib import Path
import json

from django.conf import settings
from django.http import JsonResponse, Http404
from django.shortcuts import render


CONTRACT_FILES = {
    "accounts": "accounts_api_contract.json",
    "ai": "ai_api_contract.json",
    "attachments": "attachments_api_contract.json",
    "appointments": "appointments_api_contract.json",
    "community": "community_api_contract.json",
    "evaluations": "evaluations_api_contract.json",
    "universities": "universities_api_contract.json",
    "messaging": "messaging_api_contract.json",
    "notifications": "notifications_api_contract.json",
    "audit": "audit_api_contract.json",
    "backup": "backup_api_contract.json",
    "cases": "cases_api_contract.json",
    "reports": "reports_api_contract.json",
    "support": "support_api_contract.json",
}


def ui_index(request):
    return render(request, "ui/index.html")


def ui_contract(request, contract):
    filename = CONTRACT_FILES.get(contract)
    if not filename:
        raise Http404("Unknown contract.")

    contract_path = Path(settings.BASE_DIR) / filename
    if not contract_path.exists():
        fallback_path = Path(settings.BASE_DIR) / "endpoint" / filename
        if fallback_path.exists():
            contract_path = fallback_path
        else:
            raise Http404("Contract file not found.")

    with contract_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    return JsonResponse(data)
