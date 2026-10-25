"""Prepare detailed, review-only migration proposals from qualified artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def prepare(decisions_path: Path, task_repairs_path: Path, graph_repairs_path: Path, checklist_path: Path, output_json: Path, output_md: Path) -> dict:
    decisions = _load(decisions_path)
    task_repairs = _load(task_repairs_path)
    graph = _load(graph_repairs_path)
    checklist = _load(checklist_path)
    current_graph = graph["sources"]["current"]
    task_review = [row for row in decisions["tasks"] if row.get("decision") == "review_required"]
    project_review = [row for row in decisions["projects"] if row.get("decision") == "review_required"]
    review_by_project = Counter(row["project_id"] for row in task_review)
    proposals = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "proposal_only",
        "ready_for_cutover": False,
        "sequence": [
            {"phase": "P0", "name": "Qualification post-L9", "action": "qualifier PostgreSQL équipe et les piles globales RepoWise, Headroom, Gemini Router, Gateway, Scheduler, réseau et OTLP/Langfuse avant la migration de production", "gate": "tous les endpoints, schémas, identifiants et retours arrière sont testés sur une copie hors production"},
            {"phase": "P1", "name": "Gel et nouvelle capture", "action": "arrêter tous les écrivains, confirmer l'arrêt de l'autre poste, attendre la stabilité Dropbox, capturer des copies SQLite sans WAL et leurs empreintes", "gate": "empreintes et comptes figés ; toute mutation invalide la fenêtre"},
            {"phase": "P2", "name": "Clôture des décisions", "action": "approuver les racines des projets, les valeurs gagnantes par champ, les projets provisoires et la politique de quarantaine du graphe", "gate": "aucun élément de revue non classé"},
            {"phase": "P3", "name": "Répétition indépendante", "action": "restaurer la candidate dans un environnement indépendant et exécuter les contrôles API, recherche, impact, scheduler, réseau et OTLP", "gate": "intégrité et FK correctes et répétition du retour arrière réussie"},
            {"phase": "P4", "name": "Bascule de production", "action": "publier une génération immuable, maintenir le scheduler arrêté, basculer les lecteurs puis réactiver les écrivains dans une fenêtre observée", "gate": "smoke tests réussis et responsable du retour arrière présent"},
        ],
        "proposals": {
            "projects": {
                "decision": "keep current-only projects; retain same-id projects pending root/owner approval; import xtream_universal_manager only after validating its root",
                "review_items": project_review,
                "task_project_repairs": task_repairs["proposals"],
                "acceptance": "every project has one approved root_path, owner, status and provenance record; no provisional project remains unapproved",
            },
            "tasks": {
                "shared_without_material_conflict": decisions["counts"]["tasks"] - decisions["counts"]["task_review_required"] - 42,
                "review_required": len(task_review),
                "review_by_project": dict(review_by_project),
                "conflicts_by_field": decisions["counts"]["field_conflicts_by_name"],
                "representative_items": task_review[:25],
                "rule": "preserve content only when equal; otherwise choose field-by-field from evidence (worktree existence, status transition, steps monotonicity, metadata merge, title provenance) and record both source values",
                "acceptance": "zero task_review_required and every chosen field has source, timestamp and reviewer evidence",
            },
            "graph": {
                "current_missing_identifiers": current_graph["missing_identifiers"],
                "deterministic_candidate_identifiers": current_graph["candidate_identifiers"],
                "candidate_edges": current_graph["candidate_edges"],
                "quarantine_edges": current_graph["quarantine_edges"],
                "policy": "apply only exact file-prefix and unique-function-suffix repairs; keep all other edges in quarantine; deduplicate only after remapping and retain source_rows plus source hash",
                "acceptance": "zero FK violations in the active projection, reachability equal at depth 2, quarantine export restorable, and no consumer relying on raw row IDs",
            },
            "scheduler": {
                "decision": "archive run_history separately; keep jobs disabled through cutover and first observation window",
                "acceptance": "archive integrity ok, no historical command executed, explicit activation approval after smoke tests",
            },
        },
        "blocking_evidence": checklist["blockers"],
        "required_approvals": ["project ownership and roots", "task field conflict winners", "quarantine retention policy", "PostgreSQL/global stack readiness", "cutover and rollback window"],
        "policy": "proposal only; no source or operational database is modified",
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(proposals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = [
        "# Propositions détaillées — migration globale DevCore",
        "",
        f"Généré le {proposals['created_utc']}. Statut : **proposal_only** ; bascule autorisée : **non**.",
        "",
        "## Ordre proposé",
        "",
        "| Phase | Action | Critère de sortie |",
        "|---|---|---|",
    ]
    md.extend(f"| {p['phase']} — {p['name']} | {p['action']} | {p['gate']} |" for p in proposals["sequence"])
    md += [
        "",
        "## Projets et tâches",
        "",
        f"Trois projets ont un identifiant commun mais des racines ou horodatages différents. Les 33 tâches `xtream_universal_manager` nécessitent la validation de la racine `C:\\src\\xtream_universal_manager`; les 13 tâches `scripts` nécessitent un projet provisoire approuvé.",
        "",
        f"Les conflits matériels concernent {len(task_review)} tâches : " + ", ".join(f"{k}={v}" for k, v in decisions["counts"]["field_conflicts_by_name"].items()) + ". Répartition : " + ", ".join(f"{k}={v}" for k, v in review_by_project.most_common()) + ".",
        "",
        "Règle proposée : arbitrage champ par champ, conservation des deux valeurs sources et de la preuve ; aucune victoire globale d’une base.",
        "",
        "## Graphe",
        "",
        f"Sur la copie actuelle, {current_graph['candidate_edges']} arêtes sont réparables par règle déterministe et {current_graph['quarantine_edges']} restent en quarantaine. Les relations sans preuve restent hors projection FK. La déduplication ne doit intervenir qu’après remappage et doit conserver `source_rows` et l’empreinte de la source.",
        "",
        "## Scheduler et pile post-L9",
        "",
        "La migration de production est proposée après la qualification PostgreSQL équipe et des services globaux RepoWise, Headroom, Gemini Router, Gateway, Scheduler, réseau et OTLP/Langfuse. Avant cela, seules les répétitions sur copies sont autorisées. Le scheduler reste arrêté pendant la bascule et l’observation initiale.",
        "",
        "## Approbations nécessaires",
        "",
    ]
    md.extend(f"- {item}" for item in proposals["required_approvals"])
    md += ["", "## Blocages actuels", "", "- " + "\n- ".join(checklist["blockers"]), ""]
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(md), encoding="utf-8")
    return {"output_json": str(output_json), "output_md": str(output_md), "status": "proposal_only", "ready_for_cutover": False, "blocking_items": len(checklist["blockers"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--task-repairs", type=Path, required=True)
    parser.add_argument("--graph-repairs", type=Path, required=True)
    parser.add_argument("--checklist", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.decisions, args.task_repairs, args.graph_repairs, args.checklist, args.output_json, args.output_md), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
