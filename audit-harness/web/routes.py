import json
import logging
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, render_template

from core.harness_engine import run_harness, get_auditor_prompt
from core.evaluator import get_evaluator_criteria
from core.interaction_chain import InteractionChain, _dict_to_markdown
from core.file_reader import list_files, read_file
from core import session_store
from config.settings import settings

logger = logging.getLogger(__name__)

bp = Blueprint("routes", __name__)

try:
    session_store.init_db()
except Exception as e:
    logger.warning("Session DB init failed (may be normal in tests): %s", e)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})


@bp.route("/api/list-files", methods=["POST"])
def api_list_files():
    try:
        data = request.get_json(silent=True)
        if not data or "folder_path" not in data:
            return jsonify({"error": "Missing 'folder_path' in request body"}), 400
        folder_path = data["folder_path"]
        if not os.path.isabs(folder_path):
            return jsonify({"error": "folder_path must be absolute"}), 400
        files = list_files(folder_path)
        return jsonify({"files": files})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Unexpected error in /api/list-files")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/query", methods=["POST"])
def api_query():
    try:
        data = request.get_json(silent=True)
        if not data or "query" not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400

        query = data["query"]
        folder_path = data.get("folder_path", "")
        selected_files = data.get("selected_files", [])
        session_id = data.get("session_id", None)

        file_contents = None
        if folder_path and selected_files:
            file_contents = {}
            for fname in selected_files:
                try:
                    result = read_file(folder_path, fname)
                    file_contents[result["filename"]] = result["content"]
                except (ValueError, FileNotFoundError) as e:
                    logger.warning("Skipping file %s: %s", fname, e)

        chain = run_harness(query, file_contents,
                            session_id=session_id, folder_path=folder_path)

        return jsonify({
            "session_id": chain.session_id,
            "final_output": chain.final_output,
            "total_iterations": chain.total_iterations,
            "early_stopped": chain.early_stopped,
            "chain": chain.to_dict(),
            "referenced_files": chain.referenced_files,
        })
    except RuntimeError as e:
        logger.exception("Runtime error in /api/query")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception("Unexpected error in /api/query")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/export", methods=["POST"])
def api_export():
    try:
        data = request.get_json(silent=True)
        if not data or "chain_data" not in data:
            return jsonify({"error": "Missing 'chain_data' in request body"}), 400

        chain_dict = data["chain_data"]
        folder_path = data.get("folder_path", "")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_output_{timestamp}.md"

        if folder_path:
            if not os.path.isabs(folder_path):
                return jsonify({"error": "folder_path must be absolute"}), 400
            if not os.path.isdir(folder_path):
                return jsonify({"error": f"Directory not found: {folder_path}"}), 400
            export_dir = Path(folder_path) / "exports"
        else:
            export_dir = Path(__file__).parent.parent / "exports"

        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / filename

        markdown = _dict_to_markdown(chain_dict)
        export_path.write_text(markdown, encoding="utf-8")

        return jsonify({"filename": filename, "path": str(export_path)})
    except Exception as e:
        logger.exception("Unexpected error in /api/export")
        return jsonify({"error": f"Internal error: {e}"}), 500


# === Session Management ===

@bp.route("/api/sessions", methods=["GET"])
def api_list_sessions():
    try:
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)
        sessions = session_store.list_sessions(limit, offset)
        return jsonify({"sessions": sessions})
    except Exception as e:
        logger.exception("Unexpected error in /api/sessions")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/sessions/<session_id>", methods=["GET"])
def api_get_session(session_id):
    try:
        session = session_store.load_session(session_id)
        return jsonify(session)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception("Unexpected error in /api/sessions/<id>")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/sessions/<session_id>/continue", methods=["POST"])
def api_continue_session(session_id):
    try:
        data = request.get_json(silent=True)
        if not data or "query" not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400

        query = data["query"]
        selected_files = data.get("selected_files", [])
        prior = session_store.load_session(session_id)
        folder_path = prior.get("folder_path", "")

        file_contents = None
        if folder_path and selected_files:
            file_contents = {}
            for fname in selected_files:
                try:
                    result = read_file(folder_path, fname)
                    file_contents[result["filename"]] = result["content"]
                except (ValueError, FileNotFoundError) as e:
                    logger.warning("Skipping file %s: %s", fname, e)

        chain = run_harness(query, file_contents,
                            session_id=session_id, folder_path=folder_path)

        return jsonify({
            "session_id": chain.session_id,
            "final_output": chain.final_output,
            "total_iterations": chain.total_iterations,
            "early_stopped": chain.early_stopped,
            "chain": chain.to_dict(),
            "referenced_files": chain.referenced_files,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except RuntimeError as e:
        logger.exception("Runtime error in continue session")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception("Unexpected error in continue session")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/sessions/<session_id>/title", methods=["PUT"])
def api_rename_session(session_id):
    try:
        data = request.get_json(silent=True)
        title = data.get("title", "") if data else ""
        session = session_store.load_session(session_id)
        chain_data = session.get("chain")
        if isinstance(chain_data, str):
            chain_data = json.loads(chain_data)
        session_store.save_session(
            session_id, title, session.get("folder_path", ""),
            chain_data or session.get("chain", {}),
            bool(session.get("is_complete", 1)),
            session.get("summary", ""))
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception("Unexpected error in rename session")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/sessions/<session_id>", methods=["DELETE"])
def api_delete_session(session_id):
    try:
        session_store.delete_session(session_id)
        return jsonify({"ok": True})
    except Exception as e:
        logger.exception("Unexpected error in delete session")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/sessions", methods=["DELETE"])
def api_clear_sessions():
    try:
        session_store.clear_all_sessions()
        return jsonify({"ok": True})
    except Exception as e:
        logger.exception("Unexpected error in clear sessions")
        return jsonify({"error": f"Internal error: {e}"}), 500


# === Settings Editor ===

@bp.route("/api/settings", methods=["GET"])
def api_get_settings():
    try:
        return jsonify(settings.to_dict())
    except Exception as e:
        logger.exception("Unexpected error in get settings")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/settings/<field_name>", methods=["PUT"])
def api_update_setting(field_name):
    try:
        data = request.get_json(silent=True)
        if not data or "value" not in data:
            return jsonify({"error": "Missing 'value' in request body"}), 400
        value = str(data["value"])
        settings.update_field(field_name, value)
        return jsonify({"ok": True, "field": field_name})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Unexpected error in update setting")
        return jsonify({"error": f"Internal error: {e}"}), 500


# === Prompts ===

@bp.route("/api/prompts/<prompt_type>", methods=["GET"])
def api_get_prompt(prompt_type):
    try:
        prompt_dir = Path(__file__).parent.parent / "prompts"
        filename_map = {"auditor": "system_auditor.md", "evaluator": "evaluator_criteria.md"}
        if prompt_type not in filename_map:
            return jsonify({"error": "Invalid prompt type"}), 400
        content = (prompt_dir / filename_map[prompt_type]).read_text(encoding="utf-8")
        return jsonify({"content": content, "type": prompt_type})
    except Exception as e:
        logger.exception("Unexpected error in get prompt")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/prompts/<prompt_type>", methods=["PUT"])
def api_update_prompt(prompt_type):
    try:
        prompt_dir = Path(__file__).parent.parent / "prompts"
        filename_map = {"auditor": "system_auditor.md", "evaluator": "evaluator_criteria.md"}
        if prompt_type not in filename_map:
            return jsonify({"error": "Invalid prompt type"}), 400
        data = request.get_json(silent=True)
        if not data or "content" not in data:
            return jsonify({"error": "Missing 'content' in request body"}), 400
        content = data["content"]
        (prompt_dir / filename_map[prompt_type]).write_text(content, encoding="utf-8")
        return jsonify({"ok": True, "type": prompt_type})
    except Exception as e:
        logger.exception("Unexpected error in update prompt")
        return jsonify({"error": f"Internal error: {e}"}), 500


# === Skill Learning ===

@bp.route("/api/skills", methods=["GET"])
def api_list_skills():
    try:
        skills = session_store.list_learned_skills(active_only=False)
        return jsonify({"skills": skills})
    except Exception as e:
        logger.exception("Unexpected error in list skills")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/skills/learn", methods=["POST"])
def api_trigger_learning():
    try:
        from core.skill_learner import learn_from_sessions
        new_skills = learn_from_sessions()
        return jsonify({"new_skills": new_skills, "count": len(new_skills)})
    except Exception as e:
        logger.exception("Unexpected error in trigger learning")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/skills/<int:skill_id>", methods=["PUT"])
def api_update_skill(skill_id):
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        skill_text = data.get("skill_text")
        is_active = data.get("is_active")
        session_store.update_learned_skill(skill_id, skill_text=skill_text, is_active=is_active)
        return jsonify({"ok": True})
    except Exception as e:
        logger.exception("Unexpected error in update skill")
        return jsonify({"error": f"Internal error: {e}"}), 500


@bp.route("/api/skills/<int:skill_id>", methods=["DELETE"])
def api_delete_skill(skill_id):
    try:
        session_store.delete_learned_skill(skill_id)
        return jsonify({"ok": True})
    except Exception as e:
        logger.exception("Unexpected error in delete skill")
        return jsonify({"error": f"Internal error: {e}"}), 500
