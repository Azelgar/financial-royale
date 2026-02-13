import streamlit as st
import json
import os
import sys
import random
import psycopg2
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), 'engine'))
from engine import Engine

# ==========================
# CONFIG
# ==========================

with open("config.json") as f:
    config = json.load(f)

engine = Engine(config)

DATABASE_URL = os.environ.get("DATABASE_URL")
DOCENTE_PASSWORD = os.environ.get("DOCENTE_PASSWORD")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

with open("database/schema.sql") as f:
    cursor.execute(f.read())

st.title("Financial Royale v5 - Plataforma Académica")

# ==========================
# LOGIN SIMPLE
# ==========================

if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:

    role_choice = st.radio("Selecciona Rol", ["Alumno", "Docente"])

    if role_choice == "Docente":
        password_input = st.text_input("Contraseña Docente", type="password")

        if st.button("Ingresar"):
            if password_input == DOCENTE_PASSWORD:
                st.session_state.role = "Docente"
                st.rerun()
            else:
                st.error("Contraseña incorrecta")

    else:
        if st.button("Ingresar como Alumno"):
            st.session_state.role = "Alumno"
            st.rerun()

    st.stop()

# ==========================
# MENÚ SEGÚN ROL
# ==========================

role = st.session_state.role

st.sidebar.write(f"Rol actual: {role}")

if st.sidebar.button("Cerrar sesión"):
    st.session_state.role = None
    st.rerun()

# ==========================
# MENÚ DOCENTE
# ==========================

if role == "Docente":

    menu = st.sidebar.selectbox(
        "Menú Docente",
        ["Crear Cohorte", "Crear Jugador", "Dashboard Cohorte", "Ranking Global"]
    )

    # Crear Cohorte
    if menu == "Crear Cohorte":

        name = st.text_input("Nombre cohorte")

        if st.button("Crear Cohorte"):
            shock_week = random.randint(
                config["shock_week_min"],
                config["shock_week_max"]
            )

            severity = random.choice([
                config["shock_sev_low"],
                config["shock_sev_mid"],
                config["shock_sev_high"]
            ])

            cursor.execute(
                "INSERT INTO cohorts (name, shock_week, shock_severity) VALUES (%s, %s, %s)",
                (name, shock_week, severity)
            )

            st.success("Cohorte creada")

    # Crear Jugador
    elif menu == "Crear Jugador":

        cursor.execute("SELECT id, name FROM cohorts")
        cohorts = cursor.fetchall()

        if not cohorts:
            st.warning("Primero crea una cohorte.")
        else:
            cohort_dict = {c[1]: c[0] for c in cohorts}

            selected = st.selectbox(
                "Seleccionar cohorte",
                list(cohort_dict.keys())
            )

            name = st.text_input("Nombre jugador")

            if st.button("Registrar Jugador"):
                cursor.execute(
                    "INSERT INTO players (name, cohort_id, capital) VALUES (%s, %s, %s)",
                    (name, cohort_dict[selected], config["capital_inicial"])
                )
                st.success("Jugador registrado")

    # Dashboard Cohorte
    elif menu == "Dashboard Cohorte":

        cursor.execute("SELECT COUNT(*) FROM players")
        total_players = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(capital) FROM players")
        avg_capital = cursor.fetchone()[0]

        st.metric("Total Jugadores", total_players)
        st.metric("Capital Promedio", round(avg_capital or 0, 2))

    # Ranking Global
    elif menu == "Ranking Global":

        cursor.execute("SELECT id, name, capital FROM players")
        players = cursor.fetchall()

        ranking = sorted(players, key=lambda x: x[2], reverse=True)

        for i, p in enumerate(ranking, 1):
            st.write(f"{i}. {p[1]} - {round(p[2],2)}")

# ==========================
# MENÚ ALUMNO
# ==========================

elif role == "Alumno":

    menu = st.sidebar.selectbox(
        "Menú Alumno",
        ["Jugar Semana", "Ranking"]
    )

    if menu == "Jugar Semana":

        cursor.execute("SELECT id, name, cohort_id FROM players")
        players = cursor.fetchall()

        if not players:
            st.warning("No hay jugadores.")
        else:

            player_dict = {
                f"{p[1]} (ID {p[0]})": p for p in players
            }

            selected = st.selectbox(
                "Seleccionar jugador",
                list(player_dict.keys())
            )

            player_id, name, cohort_id = player_dict[selected]

            L = st.slider("Apalancamiento", 1.0, 3.0, 2.0)
            coverage = st.slider("Cobertura", 0.0, 1.0, 0.3)

            cursor.execute(
                "SELECT capital, week FROM players WHERE id=%s",
                (player_id,)
            )

            player_data = cursor.fetchone()

            if player_data:

                capital, week = player_data

                if week >= config["max_weeks"]:
                    st.warning("Ya completaste las 10 semanas.")
                else:

                    if st.button("Ejecutar Semana"):

                        with conn:

                            r = engine.generate_return()
                            adj_r = engine.adjusted_return(L, r)
                            exposure = L * 0.6

                            cursor.execute(
                                "SELECT shock_week, shock_severity FROM cohorts WHERE id=%s",
                                (cohort_id,)
                            )

                            shock_week, severity = cursor.fetchone()

                            shock = engine.shock_impact(
                                week,
                                capital,
                                exposure,
                                coverage,
                                shock_week,
                                severity
                            )

                            capital_updated = capital * (1 + adj_r) - shock
                            week_updated = week + 1

                            cursor.execute(
                                "UPDATE players SET capital=%s, week=%s WHERE id=%s",
                                (capital_updated, week_updated, player_id)
                            )

                            cursor.execute(
                                "INSERT INTO history (player_id, week, capital) VALUES (%s, %s, %s)",
                                (player_id, week_updated, capital_updated)
                            )

                            st.success(
                                f"Nuevo capital: {round(capital_updated, 2)}"
                            )

    elif menu == "Ranking":

        cursor.execute("SELECT name, capital FROM players ORDER BY capital DESC")
        ranking = cursor.fetchall()

        for i, r in enumerate(ranking, 1):
            st.write(f"{i}. {r[0]} - {round(r[1],2)}")
