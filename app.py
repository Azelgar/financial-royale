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

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

# Ejecutar schema (seguro por IF NOT EXISTS)
with open("database/schema.sql") as f:
    cursor.execute(f.read())

st.title("Financial Royale MVP v4 - Institucional")

menu = st.sidebar.selectbox(
    "Menú",
    ["Crear Cohorte", "Crear Jugador", "Jugar Semana", "Ranking"]
)

# ==========================
# CREAR COHORTE
# ==========================

if menu == "Crear Cohorte":

    name = st.text_input("Nombre cohorte")

    if st.button("Crear"):

        try:
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

        except Exception:
            st.error("Error al crear cohorte.")

# ==========================
# CREAR JUGADOR
# ==========================

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

        if st.button("Registrar"):

            try:
                cursor.execute(
                    "INSERT INTO players (name, cohort_id, capital) VALUES (%s, %s, %s)",
                    (name, cohort_dict[selected], config["capital_inicial"])
                )

                st.success("Jugador registrado")

            except Exception:
                st.error("Error al registrar jugador.")

# ==========================
# JUGAR SEMANA
# ==========================

elif menu == "Jugar Semana":

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

        if not player_data:
            st.error("Jugador inválido.")
        else:

            capital, week = player_data

            if week >= config["max_weeks"]:
                st.warning("Jugador ya completó las 10 semanas.")
            else:

                if st.button("Ejecutar Semana"):

                    try:
                        with conn:

                            r = engine.generate_return()
                            adj_r = engine.adjusted_return(L, r)
                            exposure = L * 0.6

                            cursor.execute(
                                "SELECT shock_week, shock_severity FROM cohorts WHERE id=%s",
                                (cohort_id,)
                            )

                            shock_data = cursor.fetchone()

                            if not shock_data:
                                st.error("Cohorte inválida.")
                                st.stop()

                            shock_week, severity = shock_data

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

                    except Exception:
                        st.error("Error interno al ejecutar semana.")

# ==========================
# RANKING
# ==========================

elif menu == "Ranking":

    cursor.execute("SELECT id, name, capital FROM players")
    players = cursor.fetchall()

    ranking = []

    for p in players:

        cursor.execute(
            "SELECT capital FROM history WHERE player_id=%s ORDER BY week",
            (p[0],)
        )

        history_rows = cursor.fetchall()
        history = [h[0] for h in history_rows]

        if history:
            ic = engine.calculate_ic(history)
        else:
            ic = 0

        ranking.append((p[1], p[2], ic))

    ranking.sort(key=lambda x: x[2], reverse=True)

    st.subheader("Ranking por IC")

    for i, r in enumerate(ranking, 1):
        st.write(
            f"{i}. {r[0]} - Capital: {round(r[1], 2)} - IC: {round(r[2], 4)}"
        )

    if players:

        player_names = [p[1] for p in players]

        selected_name = st.selectbox(
            "Ver evolución jugador",
            player_names
        )

        pid = next(
            p[0] for p in players if p[1] == selected_name
        )

        cursor.execute(
            "SELECT capital FROM history WHERE player_id=%s ORDER BY week",
            (pid,)
        )

        history_rows = cursor.fetchall()
        history = [h[0] for h in history_rows]

        if history:
            plt.figure()
            plt.plot(history)
            plt.title("Evolución del Capital")
            plt.xlabel("Semana")
            plt.ylabel("Capital")
            st.pyplot(plt)
