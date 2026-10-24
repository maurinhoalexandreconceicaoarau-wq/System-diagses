import csv
import sqlite3
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import quote

import streamlit as st

from backend.admin import (
    TABLES,
    delete_row,
    delete_user,
    list_rows,
    list_users,
    save_row,
    update_user_role,
)
from backend.auth import admin_exists, authenticate, create_account, get_account, set_password
from backend.history import get_consultation_history, get_history_counts, save_consultation
from expert_system.consultation import Consultation
from expert_system.knowledge_base import get_all_symptoms


st.set_page_config(page_title="Sistema Expert Moras Isin", page_icon="🩺", layout="wide")


with (Path(__file__).resolve().parent / "assets" / "theme.css").open("r", encoding="utf-8") as theme_file:
    st.markdown(f"<style>{theme_file.read()}</style>", unsafe_allow_html=True)


def show_hero(title, subtitle, badge="Kuidadu kulit"):
    st.markdown(f"""
    <section class="skin-hero">
      <div class="hero-layout">
        <div>
          <span class="hero-kicker">{escape(badge.upper())}</span>
          <h1>{escape(title)}</h1>
          <p>{escape(subtitle)}</p>
          <div class="hero-pills"><span>✦ Konsulta ho matenek</span><span>♡ Kuidadu kulit</span></div>
        </div>
        <div class="hero-art" aria-hidden="true">
          <div class="hero-orbit"></div>
          <div class="hero-icon">
            <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M50 10 78 21v23c0 21-11 35-28 46C33 79 22 65 22 44V21L50 10Z" stroke="#E9FFF3" stroke-width="4" stroke-linejoin="round"/>
              <path d="M39 52c8-15 19-18 28-17-1 13-8 27-25 29m7-5c-1-8-5-14-12-19" stroke="#BCEBC9" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="m69 29 2 5 5 2-5 2-2 5-2-5-5-2 5-2 2-5Z" fill="#FFB18C"/>
            </svg>
          </div>
        </div>
      </div>
    </section>
    """, unsafe_allow_html=True)


def show_workspace_topbar(current_user, page):
    username = escape(str(current_user.get("username", "Utilizadór")))
    initial = escape(username[:1].upper() or "U")
    role = "Administradór" if current_user.get("role") == "admin" else "Utilizadór"
    st.markdown(f"""
    <div class="workspace-topbar">
      <div class="workspace-greeting">
        <span class="workspace-kicker">DERMA CARE <i>/</i> {escape(page)}</span>
        <strong>Bem-vindu fali, {username}</strong>
        <span>Informasaun no kuidadu ba saúde kulit.</span>
      </div>
      <div class="workspace-profile">
        <span class="workspace-avatar">{initial}</span>
        <span><b>{username}</b><small>{role}</small></span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def submit_consultation(symptom_ids):
    selected_symptoms = [
        symptom_id
        for symptom_id in symptom_ids
        if st.session_state.get(f"symptom_{symptom_id}", False)
    ]
    if selected_symptoms:
        result = Consultation().analyze(selected_symptoms)
        st.session_state["consultation_results"] = result
        st.session_state["consultation_selected_symptoms"] = selected_symptoms
        st.session_state.pop("consultation_error", None)
        symptoms_by_id = {item["symptom_id"]: item for item in get_all_symptoms()}
        selected_details = [
            {
                "code": symptoms_by_id[symptom_id]["kode_sintoma"],
                "name": symptoms_by_id[symptom_id]["naran_sintoma"],
            }
            for symptom_id in selected_symptoms
            if symptom_id in symptoms_by_id
        ]
        user = st.session_state.get("user")
        if user:
            try:
                save_consultation(user, selected_details, result)
                st.session_state["history_saved"] = True
            except sqlite3.Error:
                st.session_state["history_saved"] = False
    else:
        st.session_state["consultation_results"] = None
        st.session_state["consultation_selected_symptoms"] = []
        st.session_state["consultation_error"] = "Favor hili sintoma ida uluk."

    # Reset the form selections after saving this consultation's result.
    for symptom_id in symptom_ids:
        st.session_state[f"symptom_{symptom_id}"] = False


def show_first_admin_setup():
    show_hero("Kria konta admin", "Konfigura konta administradór atu hahú jere sistema.", "Setup inicial")
    st.title("Konfigura Admin")
    st.info("Konta admin seidauk iha. Kria konta admin dahuluk atu hahú uza sistema.")
    with st.form("first_admin_form"):
        username = st.text_input("Username admin")
        password = st.text_input("Password (mínimu 8 karakter)", type="password")
        confirmation = st.text_input("Konfirma password", type="password")
        submitted = st.form_submit_button("Kria admin", type="primary")
    if submitted:
        if password != confirmation:
            st.error("Password la hanesan.")
        else:
            try:
                create_account(username, password, "admin")
                st.success("Admin kria ona. Agora bele tama ho konta foun.")
                st.rerun()
            except (ValueError, sqlite3.IntegrityError) as error:
                st.error(f"La konsege kria admin: {error}")


def show_login():
    st.markdown(
        '<aside class="login-brand-rail"><span>DERMA CARE</span><b>TAMA BA SISTEMA</b></aside>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([0.95, 1.05], gap="large", vertical_alignment="center")
    with left:
        st.markdown('<div class="login-form-anchor"></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            st.markdown('<div class="login-kicker">KUIDADU KULIT</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-title">Bem-vindu fali</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-copy">Tama ho konta atu komesa konsultasaun no aprende kona-ba moras kulit.</div>', unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Hakerek username")
            password = st.text_input("Password", placeholder="Hakerek password", type="password")
            submitted = st.form_submit_button("TAMA", type="primary", use_container_width=True)
            st.markdown('<div class="login-footnote">Konta la iha? Kontaktu administradór.</div>', unsafe_allow_html=True)
    with right:
        st.markdown("""
        <div class="login-visual" aria-hidden="true">
          <div class="login-orbit login-orbit-a"></div>
          <div class="login-orbit login-orbit-b"></div>
          <span class="login-bubble bubble-one"></span><span class="login-bubble bubble-two"></span>
          <span class="login-bubble bubble-three"></span><span class="login-bubble bubble-four"></span>
          <div class="login-illustration">
            <svg viewBox="0 0 420 360" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="shield" x1="110" y1="40" x2="300" y2="310" gradientUnits="userSpaceOnUse"><stop stop-color="#fff"/><stop offset="1" stop-color="#bde7ff"/></linearGradient>
                <linearGradient id="leaf" x1="155" y1="200" x2="285" y2="70" gradientUnits="userSpaceOnUse"><stop stop-color="#ffb7a5"/><stop offset="1" stop-color="#ffdf9b"/></linearGradient>
              </defs>
              <ellipse cx="210" cy="316" rx="130" ry="20" fill="#073fa9" opacity=".26"/>
              <path d="M210 34 310 74v87c0 80-43 133-100 166-57-33-100-86-100-166V74l100-40Z" fill="url(#shield)"/>
              <path d="M210 56 289 88v72c0 64-31 107-79 137-48-30-79-73-79-137V88l79-32Z" fill="#e7f1ff"/>
              <path d="M210 235c-27-23-61-45-61-80 0-23 29-35 61-7 32-28 61-16 61 7 0 35-34 57-61 80Z" fill="#ff9f91"/>
              <path d="M209 214c-4-35 4-69 25-98 16-22 36-33 57-36-1 29-11 54-33 73-16 14-32 20-49 23" fill="url(#leaf)"/>
              <path d="M209 217c-5-27-18-48-42-65-19-14-39-19-58-16 7 24 21 43 43 54 19 10 38 14 57 14" fill="#54b89e"/>
              <path d="M209 218c1-30 13-53 35-73M208 218c-7-20-21-35-43-47" fill="none" stroke="#187f7b" stroke-width="5" stroke-linecap="round"/>
              <circle cx="316" cy="116" r="13" fill="#ffd36f"/><circle cx="102" cy="180" r="9" fill="#ff9f91"/>
              <path d="m319 78 5 12 12 5-12 5-5 12-5-12-12-5 12-5 5-12Z" fill="#fff"/>
              <path d="m104 115 4 9 9 4-9 4-4 9-4-9-9-4 9-4 4-9Z" fill="#fff" opacity=".9"/>
            </svg>
          </div>
          <div class="login-visual-copy"><strong>Kuidadu kulit, hahu husi hatene.</strong><span>Informasaun orientativu no konsultasaun iha fatin ida.</span></div>
        </div>
        """, unsafe_allow_html=True)
    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state["user"] = user
            st.rerun()
        with left:
            st.error("Username ka password sala.")


def show_consultation():
    show_hero("Konsulta kulit", "Hili sintoma sira ne'ebé ita sente. Sistema sei buka regra ne'ebé kompatível.", "Konsultasaun")
    st.header("Konsultasaun moras kulit")
    st.write("Hili sintoma sira ne'ebé ita boot sente atu buka posibilidade moras kulit.")
    symptoms = get_all_symptoms()
    if not symptoms:
        st.error("La konsege lee lista sintoma husi database.")
        return

    st.subheader("Hili sintoma")
    st.caption("Hili sintoma sira, depois klik button atu hetan rezultadu.")
    symptom_ids = [symptom["symptom_id"] for symptom in symptoms]
    with st.form("consultation_form"):
        columns = st.columns(3)
        for index, symptom in enumerate(symptoms):
            column = columns[index % len(columns)]
            label = f"{symptom['kode_sintoma']} — {symptom['naran_sintoma']}"
            column.checkbox(label, key=f"symptom_{symptom['symptom_id']}")
            column.caption(f"Bobot: {float(symptom.get('bobot', 0.25)):.2f}")
        st.form_submit_button(
            "Analiza sintoma",
            type="primary",
            use_container_width=True,
            on_click=submit_consultation,
            args=(symptom_ids,),
        )

    if st.session_state.get("consultation_error"):
        st.warning(st.session_state["consultation_error"])
    result = st.session_state.get("consultation_results")
    if result:
        st.divider()
        st.subheader("Rezultadu konsultasaun ikus")
        history_saved = st.session_state.pop("history_saved", None)
        if history_saved is True:
            st.success("Konsultasaun rai ona iha istória.")
        elif history_saved is False:
            st.warning("Rezultadu mosu, maibé la konsege rai iha istória.")
        selected_ids = set(st.session_state.get("consultation_selected_symptoms", []))
        selected_labels = [
            f"{symptom['kode_sintoma']} — {symptom['naran_sintoma']}"
            for symptom in symptoms
            if symptom["symptom_id"] in selected_ids
        ]
        st.write("**Gejala yang dipilih:** " + ", ".join(selected_labels))
        st.info("Persentajen sira hatudu estimasaun relativa husi regra no peso global. La'os probabilidade klinika ka konfirmasaun diagnóstiku.")
        if result["status"] == "no_result":
            st.info(result["message"])
        else:
            disease = result["results"][0]
            st.markdown(f"### Problema ne'ebé hetan: {disease['naran_moras']}")
            st.progress(disease["score"] / 100, text=f"Kecocokan ho regra: {disease['score']}%")
            if disease["score"] < 50:
                st.warning("Kecocokan seidauk aas. Rezultadu nee la bele konfirma diagnóstiku; hili tan sintoma ka buka avaliasaun profisionál saúde.")
            st.markdown("**Solusaun simples**")
            if disease.get("solusi"):
                st.write(disease["solusi"])
            else:
                st.write("Konsulta ho profisionál saúde atu konfirma kondisaun no hetan tratamentu apropriadu.")
        st.caption("Rezultadu sistema nee hanesan informasaun de'it; ba avaliasaun no tratamentu, konsulta ho profisionál saúde.")


def _history_table_rows(history, include_user=False):
    rows = []
    for item in history:
        row = {
            "Oras": item["created_at"],
            "Sintoma ne'ebé hili": item["selected_symptoms_text"],
            "Rezultadu": item["result"],
            "Kecocokan": f"{item['score']}%" if item["score"] is not None else "-",
        }
        if include_user:
            row = {"Utilizadór": item["username"], **row}
        rows.append(row)
    return rows


def show_history(current_user):
    is_admin = current_user["role"] == "admin"
    history = get_consultation_history(None if is_admin else current_user["user_id"], limit=None)
    show_hero("Istória konsultasaun", "Haree fila-fali sintoma, rezultadu, no solusaun husi konsultasaun sira ne'ebé rai ona.", "Istória")
    st.header("Istória konsultasaun")
    st.write("Rezultadu konsultasaun ne'ebé rai ona.")
    if not history:
        st.info("Seidauk iha konsultasaun ne'ebé rai iha istória.")
        return

    successful = [item for item in history if item["status"] == "success"]
    scored = [item for item in successful if item["score"] is not None]
    average_score = round(sum(float(item["score"]) for item in scored) / len(scored)) if scored else 0
    disease_count = len({item["disease_name"] for item in successful if item["disease_name"]})
    summary = st.columns(4)
    summary[0].metric("Total konsultasaun", len(history))
    summary[1].metric("Rezultadu hetan", len(successful))
    summary[2].metric("Moras diferente", disease_count)
    summary[3].metric("Kecocokan mediu", f"{average_score}%")

    st.subheader("Atividade konsultasaun")
    daily_counts = Counter(item["created_at"][:10] for item in history if item["created_at"])
    daily_rows = [{"Loron": day, "Kuantidade": daily_counts[day]} for day in sorted(daily_counts)]
    disease_counts = Counter(item["disease_name"] for item in successful if item["disease_name"])
    symptom_counts = Counter(
        symptom.get("name") or symptom.get("code") or "Sintoma"
        for item in history
        for symptom in item["selected_symptoms"]
    )

    trend_col, disease_col = st.columns(2)
    with trend_col:
        st.caption("Konsultasaun kada loron")
        st.area_chart(daily_rows, x="Loron", y="Kuantidade", color="#20a486")
    with disease_col:
        st.caption("Moras ne'ebé hetan")
        if disease_counts:
            disease_rows = [
                {"Moras": name, "Kuantidade": count}
                for name, count in disease_counts.most_common(10)
            ]
            st.bar_chart(disease_rows, x="Moras", y="Kuantidade", color="#f28a72")
        else:
            st.info("Seidauk iha rezultadu atu hatudu iha gráfiku.")

    symptom_col, score_col = st.columns(2)
    with symptom_col:
        st.caption("Sintoma ne'ebé hili dala barak liu")
        if symptom_counts:
            symptom_rows = [
                {"Sintoma": name, "Kuantidade": count}
                for name, count in symptom_counts.most_common(10)
            ]
            st.bar_chart(symptom_rows, x="Sintoma", y="Kuantidade", color="#5f9ee8")
        else:
            st.info("Seidauk iha sintoma iha istória.")
    with score_col:
        st.caption("Kecocokan iha konsultasaun ikus 20")
        score_history = [
            item for item in reversed(history)
            if item["status"] == "success" and item["score"] is not None
        ][-20:]
        if score_history:
            score_rows = [
                {"Konsultasaun": f"#{index}", "Kecocokan": float(item["score"])}
                for index, item in enumerate(score_history, start=1)
            ]
            st.line_chart(score_rows, x="Konsultasaun", y="Kecocokan", color="#7956c7")
        else:
            st.info("Seidauk iha pontu kecocokan atu hatudu.")

    st.caption("Rezultadu ne'ebé hetan no la hetan")
    outcome_rows = [
        {"Rezultadu": "Hetan rezultadu", "Total": len(successful)},
        {"Rezultadu": "Seidauk hetan", "Total": len(history) - len(successful)},
    ]
    st.vega_lite_chart(
        outcome_rows,
        {
            "mark": {"type": "arc", "innerRadius": 62, "cornerRadius": 6},
            "encoding": {
                "theta": {"field": "Total", "type": "quantitative"},
                "color": {
                    "field": "Rezultadu",
                    "type": "nominal",
                    "scale": {
                        "domain": ["Hetan rezultadu", "Seidauk hetan"],
                        "range": ["#20a486", "#f28a72"],
                    },
                    "legend": {"orient": "bottom"},
                },
                "tooltip": [
                    {"field": "Rezultadu", "type": "nominal"},
                    {"field": "Total", "type": "quantitative"},
                ],
            },
            "view": {"stroke": None},
        },
        use_container_width=True,
    )

    st.subheader("Konsultasaun sira")
    st.dataframe(
        _history_table_rows(history, include_user=is_admin),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Haree solusaun iha istória"):
        for item in history:
            owner = f" · {item['username']}" if is_admin else ""
            st.markdown(f"**{item['created_at']}{owner} — {item['result']}**")
            st.write(item["solution"] or "Konsulta profisionál saúde atu hetan avaliasaun.")


def show_dashboard(current_user):
    is_admin = current_user["role"] == "admin"
    user_id = None if is_admin else current_user["user_id"]
    history = get_consultation_history(user_id, limit=1000)
    total, disease_counts = get_history_counts(user_id)

    show_hero(
        "Painél administradór" if is_admin else "Painél saúde kulit",
        "Akompaña atividade, rezultadu, no kuidadu kulit iha fatin ida.",
        "Resumo sistema" if is_admin else "Resumo pesoál",
    )
    if is_admin:
        columns = st.columns(4)
        columns[0].metric("Total utilizadór", len(list_users()))
        columns[1].metric("Moras", len(list_rows("Moras")))
        columns[2].metric("Sintoma", len(list_rows("Sintoma")))
        columns[3].metric("Total konsultasaun", total)
        st.subheader("Dadus sistema")
        st.caption("Resumo kona-ba elementu prinsipál ne'ebé admin bele jere.")
        st.bar_chart(
            [
                {"Dadus": "Utilizadór", "Total": len(list_users())},
                {"Dadus": "Moras", "Total": len(list_rows("Moras"))},
                {"Dadus": "Sintoma", "Total": len(list_rows("Sintoma"))},
                {"Dadus": "Regra", "Total": len(list_rows("Regra"))},
            ],
            x="Dadus",
            y="Total",
            color="#2876d2",
        )
    else:
        successful = [item for item in history if item["status"] == "success"]
        latest = successful[0]["disease_name"] if successful else "Belum ada"
        columns = st.columns(3)
        columns[0].metric("Konsultasaun ha'u nian", total)
        columns[1].metric("Moras ne'ebé hetan", len(disease_counts))
        columns[2].metric("Rezultadu ikus", latest)

        show_disease_education()


def show_disease_education():
    data_dir = Path(__file__).resolve().parent / "database" / "dataset"
    with (data_dir / "disease_education.csv").open(encoding="utf-8-sig", newline="") as education_file:
        education_rows = list(csv.DictReader(education_file))

    st.markdown("## Hatene liutan kona-ba moras kulit")
    st.write(
        "Lee informasaun badak no haree imajen atu hatene sinal komun sira. "
        "Imajen sira mak ezemplu deit; la bele uza atu halo diagnostiku rasik."
    )
    st.caption("Imajen balun bele hatudu sinal kulit ne'ebe forte. Klik fonte atu haree lisensa no kreditu imajen.")

    for start in range(0, len(education_rows), 3):
        columns = st.columns(3)
        for column, item in zip(columns, education_rows[start:start + 3]):
            name = item["name_tetun"].encode("ascii").decode("unicode_escape")
            summary = item["summary_tetun"].encode("ascii").decode("unicode_escape")
            file_url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(item["image_filename"]) + "?width=640"
            with column:
                st.markdown(f"### {name}")
                try:
                    st.image(file_url, use_column_width=True)
                except Exception:
                    st.info("Imajen la konsege atu hatudu agora.")
                st.write(summary)
                st.caption(f"Kreditu: {item['credit']}")
                source_url = item["source_url"].replace("(", "%28").replace(")", "%29")
                st.markdown(f"[Fonte imajen no lisensa]({source_url})")


def edit_table(table_name):
    config = TABLES[table_name]
    rows = list_rows(table_name)
    st.subheader(f"{table_name} sira")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander(f"Kria ka edita {table_name.lower()}"):
        options = ["-- Kria foun --"] + [row[config["key"]] for row in rows]
        selected = st.selectbox("Hili dadus atu edita", options, key=f"edit_select_{table_name}")
        current = next((row for row in rows if row[config["key"]] == selected), {})
        with st.form(f"save_{table_name}"):
            values = {}
            for field, label in zip(config["fields"], config["labels"]):
                value = current.get(field, "")
                if field == "priority":
                    values[field] = st.number_input(label, min_value=1, value=int(value or 1), step=1)
                elif field == "bobot":
                    values[field] = st.number_input(
                        label, min_value=0.01, max_value=1.0, value=float(value or 0.25), step=0.01, format="%.2f"
                    )
                elif field == config["key"] and current:
                    values[field] = st.text_input(label, value=str(value), disabled=True)
                elif field in ("rekomendasaun", "solusi"):
                    values[field] = st.text_area(label, value=str(value or ""), height=140)
                else:
                    values[field] = st.text_input(label, value=str(value or ""))
            submitted = st.form_submit_button("Rai dadus", type="primary")
        if submitted:
            try:
                save_row(table_name, values, selected if current else None)
                st.success("Dadus rai ona.")
                st.rerun()
            except (ValueError, sqlite3.Error) as error:
                st.error(f"La konsege rai dadus: {error}")

    if rows:
        with st.expander(f"Hamos {table_name.lower()}"):
            delete_key = st.selectbox(
                f"Hili {table_name.lower()}", [row[config["key"]] for row in rows], key=f"delete_select_{table_name}"
            )
            if st.button(f"Hamos {delete_key}", key=f"delete_{table_name}"):
                try:
                    delete_row(table_name, delete_key)
                    st.success("Dadus hamos ona.")
                    st.rerun()
                except (ValueError, sqlite3.Error) as error:
                    st.error(f"La konsege hamos dadus: {error}")


def manage_accounts(current_user):
    st.subheader("Kontas utilizadór")
    users = list_users()
    st.dataframe(users, use_container_width=True, hide_index=True)
    with st.expander("Kria konta"):
        with st.form("create_user_form"):
            username = st.text_input("Username foun")
            password = st.text_input("Password (mínimu 8 karakter)", type="password")
            role = st.selectbox("Papel", ["user", "admin"])
            submitted = st.form_submit_button("Kria konta")
        if submitted:
            try:
                create_account(username, password, role)
                st.success("Konta kria ona.")
                st.rerun()
            except (ValueError, sqlite3.IntegrityError) as error:
                st.error(f"La konsege kria konta: {error}")

    other_users = [user for user in users if user["user_id"] != current_user["user_id"]]
    if other_users:
        with st.expander("Troka papel ka hamos konta"):
            target_id = st.selectbox(
                "Konta", [user["user_id"] for user in other_users],
                format_func=lambda user_id: next(
                    f"{user['username']} ({user['role']})" for user in other_users if user["user_id"] == user_id
                ),
            )
            target = next(user for user in other_users if user["user_id"] == target_id)
            new_role = st.selectbox("Papel foun", ["user", "admin"], index=0 if target["role"] == "admin" else 1)
            if st.button("Troka papel"):
                try:
                    update_user_role(target["user_id"], new_role)
                    st.success("Papel troka ona.")
                    st.rerun()
                except (ValueError, sqlite3.Error) as error:
                    st.error(f"La konsege troka papel: {error}")
            if st.button("Hamos konta", type="secondary"):
                try:
                    delete_user(target["user_id"])
                    st.success("Konta hamos ona.")
                    st.rerun()
                except (ValueError, sqlite3.Error) as error:
                    st.error(f"La konsege hamos konta: {error}")

    if users:
        with st.expander("Troka password konta"):
            target_id = st.selectbox(
                "Konta atu troka password",
                [user["user_id"] for user in users],
                format_func=lambda user_id: next(user["username"] for user in users if user["user_id"] == user_id),
            )
            with st.form("reset_password_form"):
                new_password = st.text_input("Password foun (mínimu 8 karakter)", type="password")
                submitted = st.form_submit_button("Troka password")
            if submitted:
                try:
                    set_password(target_id, new_password)
                    st.success("Password troka ona.")
                except ValueError as error:
                    st.error(str(error))


def show_admin(current_user):
    show_hero("Jere sistema", "Admin bele organiza dadus moras, sintoma, regra no konta utilizadór.", "Painél admin")
    st.header("Painél admin")
    st.write("Admin bele jere dadus moras, sintoma, regra, fonte no konta utilizadór.")
    tabs = st.tabs(list(TABLES) + ["Konta"])
    for tab, table_name in zip(tabs[:-1], list(TABLES)):
        with tab:
            edit_table(table_name)
    with tabs[-1]:
        manage_accounts(current_user)


def main():
    if not admin_exists():
        show_first_admin_setup()
        return
    user = st.session_state.get("user")
    if user is not None:
        user = get_account(user["user_id"])
        if user is None:
            st.session_state.pop("user", None)
            st.rerun()
        st.session_state["user"] = user
    if user is None:
        show_login()
        return

    with st.sidebar:
        st.markdown(
            '<div class="side-brand"><div class="side-brand-mark">✿</div>'
            '<div class="side-brand-copy"><b>DERMA CARE</b><small>SISTEMA KUIDADU KULIT</small></div></div>',
            unsafe_allow_html=True,
        )
        st.write(f"**{user['username']}** · {user['role']}")
        pages = ["Painél", "Konsulta", "Istória"]
        if user["role"] == "admin":
            pages.append("Jere sistema")
        page = st.radio("Menu", pages)
        if st.button("Sai"):
            st.session_state.pop("user", None)
            st.session_state.pop("consultation_results", None)
            st.rerun()

    show_workspace_topbar(user, page)

    if page == "Painél":
        show_dashboard(user)
    elif page == "Istória":
        show_history(user)
    elif page == "Jere sistema" and user["role"] == "admin":
        show_admin(user)
    else:
        show_consultation()


if __name__ == "__main__":
    main()
