from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import json
import os
import re  # 改行コード統一用
from datetime import datetime, timezone, timedelta  # 登録日の自動入力用

# JSTタイムゾーンの設定
JST = timezone(timedelta(hours=9))

app = Flask(__name__)
app.secret_key = "mysecretkey"  # 適宜変更してください

# projects.json の絶対パス
PROJECTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects.json")

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"プロジェクト読み込みエラー: {e}")
            return []
    return []

def save_all_projects(projects):
    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
        print("保存件数:", len(projects))
    except IOError as e:
        print(f"保存エラー: {e}")

def render_stars(rating):
    try:
        r = float(rating)
    except:
        r = 0.0
    full = int(r)
    empty = 10 - full
    return "★" * full + "☆" * empty

app.jinja_env.filters['render_stars'] = render_stars

# POST送信後は必ずリダイレクト（PRGパターン）して重複投稿を防止
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST" and "question" in request.form:
        question = request.form.get("question")
        answer = request.form.get("answer")
        # 複数の改行コードを1つに統一
        answer = re.sub(r'\n+', '\n', answer)
        rating_str = request.form.get("rating", "5")
        try:
            rating = float(rating_str)
        except:
            rating = 5.0
        tags_str = request.form.get("tags", "")
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        if len(tags) > 5:
            tags = tags[:5]
        projects = load_projects()
        new_id = max([p.get("id", 0) for p in projects] or [0]) + 1
        project = {
            "id": new_id,
            "question": question,
            "answer": answer,
            "rating": rating,
            "likes": 0,
            "tags": tags,
            "登録日": datetime.now(JST).strftime("%Y-%m-%d")  # 登録日(JST、日付のみ)
        }
        projects.append(project)
        save_all_projects(projects)
        return redirect(url_for("index"))
    # 登録日が新しい順に表示（YYYY-MM-DD形式なので文字列での降順でOK）
    sorted_projects = sorted(load_projects(), key=lambda p: p.get('登録日', ""), reverse=True)
    return render_template("index.html", projects=sorted_projects)

@app.route("/admin-login")
def admin_login():
    session["authenticated"] = True
    session["master"] = True
    return redirect(url_for("index"))

@app.route("/admin-logout")
def admin_logout():
    session.pop("master", None)
    return redirect(url_for("index"))

@app.route("/edit/<int:project_id>", methods=["GET", "POST"])
def edit(project_id):
    projects = load_projects()
    project = next((p for p in projects if p.get("id") == project_id), None)
    if not project:
        return "プロジェクトが見つかりません", 404
    if request.method == "POST":
        new_question = request.form.get("question")
        new_answer = request.form.get("answer")
        new_answer = re.sub(r'\n+', '\n', new_answer)
        new_rating_str = request.form.get("rating", "5")
        try:
            new_rating = float(new_rating_str)
        except:
            new_rating = 5.0
        new_tags_str = request.form.get("tags", "")
        new_tags = [tag.strip() for tag in new_tags_str.split(",") if tag.strip()]
        if len(new_tags) > 5:
            new_tags = new_tags[:5]
        project["question"] = new_question
        project["answer"] = new_answer
        project["rating"] = new_rating
        project["tags"] = new_tags
        save_all_projects(projects)
        return redirect(url_for("index"))
    return render_template("edit.html", project=project, project_id=project_id)

@app.route("/like/<int:project_id>", methods=["POST"])
def like(project_id):
    projects = load_projects()
    project = next((p for p in projects if p.get("id") == project_id), None)
    if not project:
        return jsonify({"error": "プロジェクトが見つかりません"}), 404
    project["likes"] = project.get("likes", 0) + 1
    save_all_projects(projects)
    return jsonify({"likes": project["likes"]})

@app.route("/unlike/<int:project_id>", methods=["POST"])
def unlike(project_id):
    projects = load_projects()
    project = next((p for p in projects if p.get("id") == project_id), None)
    if not project:
        return jsonify({"error": "プロジェクトが見つかりません"}), 404
    if project.get("likes", 0) > 0:
        project["likes"] = project.get("likes", 0) - 1
    save_all_projects(projects)
    return jsonify({"likes": project["likes"]})

@app.route("/delete/<int:project_id>")
def delete(project_id):
    if not session.get("master"):
        return "削除権限がありません", 403
    projects = load_projects()
    new_projects = [p for p in projects if p.get("id") != project_id]
    save_all_projects(new_projects)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
